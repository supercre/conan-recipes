import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import XCRun, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout
from conan.tools.microsoft import VCVars, is_msvc, msvc_runtime_flag

required_conan_version = ">=2.0"


class LuaJITConan(ConanFile):
    # 버전 끝의 -sc.N이 SC 패치를 뜻한다. ConanCenter의 luajit/2.1.<시각>은 패치 없는 업스트림 빌드다.
    name = "luajit"
    package_type = "static-library"
    license = "MIT"
    description = "LuaJIT 2.1 (rolling) static library; string keys keep the 2.1.0-beta3 pairs() order"
    url = "https://github.com/supercre/conan-recipes"
    homepage = "https://luajit.org"
    topics = ("lua", "luajit", "jit")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        # 문자열 ID를 내용 해시로 정해 pairs 순서를 beta3와 같게, 실행 이력과 무관하게 만든다(patches/0001).
        "content_strid": [True, False],
        # string.format·tostring의 반올림을 beta3처럼 0.5에서 올림으로 둔다(patches/0002). 끄면 업스트림의 짝수 반올림.
        "beta3_number_format": [True, False],
        # Lua 5.2 확장(table.pack, __pairs 등). 기존 패키지는 Windows만 켜져 있었다.
        "lua52compat": [True, False],
    }
    default_options = {
        "fPIC": True,
        "content_strid": True,
        "beta3_number_format": True,
        "lua52compat": False,
    }

    _headers = ("lua.h", "lualib.h", "lauxlib.h", "luaconf.h", "lua.hpp", "luajit.h")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "tests/*", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # C 라이브러리다. C++ 표준과 표준 라이브러리 설정은 바이너리에 영향이 없다.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # 빌드 도구(buildvm)는 대상과 같은 포인터 크기로 호스트에서 돌아야 한다. 64비트 대상만 다룬다.
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(f"{self.ref}: only armv8 and x86_64 targets are supported")
        if self.settings.os == "Windows" and not is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref}: Windows needs the msvc compiler (msvcbuild.bat)")

    def validate_build(self):
        build_os = str(self.settings_build.os)
        if self.settings.os == "Windows" and build_os != "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref}: Windows binaries are built on Windows with msvcbuild.bat. "
                "Install the published binary (--build=never) when cross building.")
        if self.settings.os != "Windows" and build_os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref}: build non-Windows targets on macOS or Linux")
        if self.settings.os == "iOS" and build_os != "Macos":
            raise ConanInvalidConfiguration(f"{self.ref}: iOS builds need Xcode on macOS")

    def source(self):
        # codeload 주소에는 확장자가 없어 압축 형식을 파일 이름으로 알려 준다.
        get(self, **self.conan_data["sources"][self.version], filename="luajit.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if is_msvc(self):
            VCVars(self).generate()
            # msvcbuild.bat의 cl 명령 뒤에 붙는다. 정적 빌드는 런타임 플래그가 없어 기본값 /MT가 되므로 소비자와 맞춘다.
            flags = [f"/{msvc_runtime_flag(self)}", "/Z7"] + [f"/D{d}" for d in self._defines]
            env = Environment()
            env.define("_CL_", " ".join(flags))
            env.vars(self, scope="build").save_script("conanbuild_luajit_cl")

    @property
    def _defines(self):
        defines = []
        if self.options.content_strid:
            defines.append("LUAJIT_SC_CONTENT_STRID=1")
        if self.options.beta3_number_format:
            defines.append("LUAJIT_SC_BETA3_NUMFMT=1")
        if self.options.lua52compat:
            defines.append("LUAJIT_ENABLE_LUA52COMPAT")
        return defines

    def _make_args(self):
        args = ["BUILDMODE=static", "Q=", f"XCFLAGS={' '.join('-D' + d for d in self._defines)}"]
        if self.settings.build_type == "Debug":
            args.append("CCDEBUG=-g")
        # 최근 Clang은 C 코드의 a*b+c를 FMA로 합친다(arm64). 그러면 math.randomseed 등의 결과가 x64·기존 빌드와 달라진다.
        target_flags = ["-ffp-contract=off"]
        if self.options.get_safe("fPIC") and not is_apple_os(self):
            target_flags.append("-fPIC")
        os_name = str(self.settings.os)

        if os_name == "Android":
            ndk = self.conf.get("tools.android:ndk_path", check_type=str)
            if not ndk:
                raise ConanException(f"{self.ref}: set tools.android:ndk_path to build for Android")
            host_tag = {"Macos": "darwin-x86_64", "Linux": "linux-x86_64"}[str(self.settings_build.os)]
            bindir = os.path.join(ndk, "toolchains", "llvm", "prebuilt", host_tag, "bin")
            triple = {"armv8": "aarch64-linux-android", "x86_64": "x86_64-linux-android"}[str(self.settings.arch)]
            api = str(self.settings.get_safe("os.api_level") or 21)
            cc = os.path.join(bindir, f"{triple}{api}-clang")
            args += [
                "HOST_CC=cc", "TARGET_SYS=Linux",
                f"CROSS={os.path.join(bindir, 'llvm-')}",
                f"STATIC_CC={cc}", f"DYNAMIC_CC={cc} -fPIC", f"TARGET_LD={cc}",
                f"TARGET_AR={os.path.join(bindir, 'llvm-ar')} rcus",
                f"TARGET_STRIP={os.path.join(bindir, 'llvm-strip')}",
            ]
        elif os_name == "iOS":
            xcrun = XCRun(self)
            simulator = self.settings.get_safe("os.sdk") == "iphonesimulator"
            version = str(self.settings.get_safe("os.version") or "13.0")
            target = f"arm64-apple-ios{version}" + ("-simulator" if simulator else "")
            if self.settings.arch == "x86_64":
                target = f"x86_64-apple-ios{version}-simulator"
            target_flags += ["-target", target, "-isysroot", xcrun.sdk_path]
            args += ["DEFAULT_CC=clang", "HOST_CC=clang", "TARGET_SYS=iOS",
                     f"CROSS={os.path.dirname(xcrun.cc)}/"]
        elif os_name == "Macos":
            arch = {"armv8": "arm64", "x86_64": "x86_64"}[str(self.settings.arch)]
            target_flags += ["-arch", arch]
            args += ["DEFAULT_CC=clang", "HOST_CC=clang",
                     f"MACOSX_DEPLOYMENT_TARGET={self.settings.get_safe('os.version') or '11.0'}"]
        args.append(f"TARGET_FLAGS={' '.join(target_flags)}")
        return args

    def build(self):
        # 빌드는 소스 트리 안에서 산출물을 만든다. 공유하는 소스 폴더를 건드리지 않도록 복사해서 빌드한다.
        copy(self, "*", self.source_folder, self.build_folder)
        src = os.path.join(self.build_folder, "src")
        if is_msvc(self):
            options = ["lua52compat"] if self.options.lua52compat else []
            self.run(" ".join(["msvcbuild.bat"] + options + ["static"]), cwd=src)
        else:
            jobs = os.cpu_count() or 4
            self.run(" ".join(["make", f"-j{jobs}"] + [shlex.quote(a) for a in self._make_args()]), cwd=src)

    def package(self):
        src = os.path.join(self.build_folder, "src")
        include = os.path.join(self.package_folder, "include", "luajit-2.1")
        for header in self._headers:
            copy(self, header, src, include)
        lib = os.path.join(self.package_folder, "lib")
        bin_folder = os.path.join(self.package_folder, "bin")
        copy(self, "lua51.lib" if is_msvc(self) else "libluajit.a", src, lib)
        if not cross_building(self):
            # 바이트코드 저장(luajit -b)에 jit/*.lua가 필요하다. Windows 기본 경로(!\lua\?.lua)와 같은 자리에 둔다.
            copy(self, "luajit.exe" if is_msvc(self) else "luajit", src, bin_folder)
            copy(self, "*.lua", os.path.join(src, "jit"), os.path.join(bin_folder, "lua", "jit"))
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "compat.lua", os.path.join(self.export_sources_folder, "tests"),
             os.path.join(self.package_folder, "res", "tests"))
        save(self, os.path.join(self.package_folder, "res", "source.json"), json.dumps({
            "source": self.conan_data["sources"][self.version],
            "patches": [p["patch_file"] for p in self.conan_data.get("patches", {}).get(self.version, [])],
            "defines": self._defines,
        }, indent=2) + "\n")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "luajit")
        self.cpp_info.set_property("cmake_target_name", "luajit::luajit")
        self.cpp_info.set_property("pkg_config_name", "luajit")
        self.cpp_info.includedirs = [os.path.join("include", "luajit-2.1")]
        self.cpp_info.libs = ["lua51"] if is_msvc(self) else ["luajit"]
        if self.settings.os in ("Linux", "FreeBSD", "Android"):
            self.cpp_info.system_libs = ["m", "dl"]
        bin_folder = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_folder):
            self.cpp_info.bindirs = ["bin"]
            if self.settings.os != "Windows":
                lua_path = os.path.join(bin_folder, "lua", "?.lua") + ";;"
                self.runenv_info.define("LUA_PATH", lua_path)
                self.buildenv_info.define("LUA_PATH", lua_path)
        else:
            self.cpp_info.bindirs = []
