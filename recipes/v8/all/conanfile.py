import json
import yaml
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import get, copy, save, move_folder_contents, mkdir, rm, rmdir, load
from conan.tools.scm import Git
from conan.errors import ConanException
import os

class V8Conan(ConanFile):
    name = "v8"
    user = "sc"
    channel = "dev"
    
    # Metadata
    description = "V8 - JavaScript Engine"
    homepage = "https://chromium.googlesource.com/v8/v8"
    license = "BSD-3-Clause"
    topics = ['javascript', 'interpreter', 'compiler', 'virtual-machine', 'javascript-engine']

    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    # export-pkg only
    build_policy = "never"

    def set_version(self):
        f = load(self, os.path.join(self.recipe_folder, 'build.yaml'))
        buildcfg_all = yaml.load(f, Loader=yaml.FullLoader)
        self.version = buildcfg_all["v8_version"]

    def layout(self):
        platform_arch = self._get_platform_arch()
        if not platform_arch:
            self.output.error(f"Unsupported platform/arch combination: {self.settings.os}/{self.settings.arch}")
            return
        platform, arch = platform_arch

        self.folders.build = "workspace"
        self.folders.source = self.folders.build
        self.folders.generators = "conan_gen"
        self.cpp.source.includedirs = ["v8/include"]
        self.cpp.build.libdirs = ["output/{}/{}/lib".format(platform, arch)]
    
    def package(self):
        """패키지 파일 복사"""
        platform, arch = self._get_platform_arch()

        include_dir = os.path.join(self.source_folder, self.cpp.source.includedirs[0])
        lib_dir = os.path.join(self.build_folder, self.cpp.build.libdirs[0])

        # lib 하위 디렉터리에 빌드 타입 폴더가 있는 경우, 해당 폴더 대상으로 복사. 그렇지 않으면 lib 폴더 대상 복사.
        build_type_dir = os.path.join(lib_dir, str(self.settings.build_type).lower())
        if os.path.isdir(build_type_dir):
            lib_dir = build_type_dir

        self.output.info(f"include_dir: {include_dir}")
        self.output.info(f"lib_dir: {lib_dir}")

        # Copy include directory
        copy(self, "*",
             src=include_dir,
             dst=os.path.join(self.package_folder, "include", "v8"),
             keep_path=True)
        
        # Copy libraries
        copy(self, "*.a",
             src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"),
             excludes="*/*",
             keep_path=False)
        copy(self, "*.lib",
             src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"),
             excludes="*/*",
             keep_path=False)

    def package_id(self):
        try:
            del self.info.settings.compiler.runtime_type
        except:
            pass
        
        settings_info = {
            "os": str(self.info.settings.os),
            "arch": str(self.info.settings.arch),
            "compiler": str(self.info.settings.compiler),
            "build_type": str(self.info.settings.build_type)
        }
        self.output.info("package_id keys: " + json.dumps(settings_info, indent=2))
            
    def package_info(self):
        """패키지 정보 설정"""

        self.cpp_info.set_property("cmake_target_name", "V8::V8")
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "v8")]
        if self.settings.os == "Windows":
            if self.settings.build_type == "Debug":
                self.cpp_info.libs = ["v8_monolith_vcD"]
            else:
                self.cpp_info.libs = ["v8_monolith_vc"]
        else:
            self.cpp_info.libs = ["v8_monolith"]

        self.output.info(f"V8 {self.version} configured with:")
        self.output.info(f"Package include dirs: {self.cpp_info.includedirs}")
        self.output.info(f"Package lib dirs: {self.cpp_info.libdirs}")

    def _get_platform_arch(self):
        """Map Conan settings to directory structure"""
        os_map = {
            "Android": "android",
            "iOS": "ios", 
            "Windows": "windows",
            "Macos": "macos"
        }
        
        arch_map = {
            "armv8": "arm64-v8a",      # Android ARM64
            "armv7": "armeabi-v7a",    # Android ARM32
            "x86": "x86",              # Android x86
            "x86_64": "x86_64",        # Android x86_64
            "armv8-32": "arm64",       # iOS ARM64
            "x86_64": "x64"            # Windows x64
        }
        
        platform = os_map.get(str(self.settings.os))
        if not platform:
            return None
            
        # Special handling for different platforms
        if self.settings.os == "iOS" and self.settings.arch in ["armv8", "armv8-32"]:
            arch = "arm64"
        elif self.settings.os == "Macos" and self.settings.arch in ["armv8", "armv8-32"]:
            arch = "arm64"
        elif self.settings.os == "Windows" and self.settings.arch == "x86_64":
            arch = "x64"
        else:
            arch = arch_map.get(str(self.settings.arch))
            
        if not arch:
            return None
            
        return platform, arch
