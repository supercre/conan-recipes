import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy


class SsrSwcBridgeConan(ConanFile):
    name = "ssr_swc_bridge"
    version = "0.1.0"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = (
        "Cargo.toml",
        "Cargo.lock",
        "src/*.rs",
        "include/*.h",
    )

    def validate(self):
        if self.settings.os not in ("Windows", "Macos", "iOS", "Android"):
            raise ConanInvalidConfiguration("ssr_swc_bridge is supported only on Windows, macOS, iOS, and Android")

    def build(self):
        manifest = os.path.join(self.source_folder, "Cargo.toml")
        target = self._rust_target()
        profile_args = []
        if str(self.settings.build_type).lower() != "debug":
            profile_args.append("--release")

        cargo_env = Environment()
        cargo_env.define("CARGO_TARGET_DIR", os.path.join(self.build_folder, "cargo"))
        rustc = self._rustc_path()
        if rustc:
            cargo_env.define("RUSTC", rustc)
        self._configure_android_cargo_env(cargo_env, target)

        with cargo_env.vars(self).apply():
            if shutil.which("rustup"):
                self.run("rustup target add {}".format(target))
            self.run(
                "{} build --manifest-path \"{}\" --target {} {}".format(
                    self._cargo_command(),
                    manifest,
                    target,
                    " ".join(profile_args),
                )
            )

    def package(self):
        target = self._rust_target()
        profile_dir = "debug"
        if str(self.settings.build_type).lower() != "debug":
            profile_dir = "release"

        cargo_dir = os.path.join(self.build_folder, "cargo", target, profile_dir)
        if self.settings.os == "Windows":
            pattern = "ssr_swc_bridge.lib"
        else:
            pattern = "libssr_swc_bridge.a"

        copied = copy(self, pattern, src=cargo_dir, dst=os.path.join(self.package_folder, "lib"))
        if not copied:
            raise ConanInvalidConfiguration("Missing ssr_swc_bridge artifact in {}".format(cargo_dir))

        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include", "swc_bridge"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ssr_swc_bridge")
        self.cpp_info.set_property("cmake_target_name", "ssr_swc_bridge::ssr_swc_bridge")
        self.cpp_info.libs = ["ssr_swc_bridge"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend([
                "advapi32",
                "bcrypt",
                "ntdll",
                "userenv",
                "ws2_32",
            ])
        elif self.settings.os in ("Macos", "iOS"):
            self.cpp_info.frameworks.extend([
                "CoreFoundation",
                "Security",
                "SystemConfiguration",
            ])
        elif self.settings.os == "Android":
            self.cpp_info.system_libs.extend([
                "dl",
                "log",
            ])

    def _rust_target(self):
        os_name = str(self.settings.os)
        arch = str(self.settings.arch)
        if os_name == "Windows":
            if arch in ("x86_64", "x64"):
                return "x86_64-pc-windows-msvc"
        elif os_name == "Macos":
            if arch in ("armv8", "arm64", "armv8.3"):
                return "aarch64-apple-darwin"
            if arch == "x86_64":
                return "x86_64-apple-darwin"
        elif os_name == "iOS":
            if arch in ("armv8", "arm64", "armv8.3"):
                return "aarch64-apple-ios"
        elif os_name == "Android":
            if arch in ("armv8", "arm64", "armv8.3"):
                return "aarch64-linux-android"
            if arch == "armv7":
                return "armv7-linux-androideabi"
            if arch == "x86":
                return "i686-linux-android"
            if arch == "x86_64":
                return "x86_64-linux-android"

        raise ConanInvalidConfiguration("Unsupported Rust target for {} {}".format(os_name, arch))

    def _configure_android_cargo_env(self, cargo_env, target):
        if self.settings.os != "Android":
            return

        ndk_path = self._android_ndk_path()
        if not ndk_path:
            raise ConanInvalidConfiguration("Android NDK path is required to build ssr_swc_bridge")

        api_level = self._android_api_level()
        linker_name = self._android_linker_name(target, api_level)
        toolchain_bin = os.path.join(
            ndk_path,
            "toolchains",
            "llvm",
            "prebuilt",
            self._android_ndk_host_tag(),
            "bin",
        )
        linker_path = os.path.join(toolchain_bin, linker_name)
        if platform.system() == "Windows":
            linker_path += ".cmd"
        if not os.path.exists(linker_path):
            raise ConanInvalidConfiguration("Missing Android Rust linker: {}".format(linker_path))

        target_env_key = target.upper().replace("-", "_")
        cargo_env.define("CARGO_TARGET_{}_LINKER".format(target_env_key), linker_path)
        cargo_env.define("AR", os.path.join(toolchain_bin, "llvm-ar"))

    def _android_ndk_path(self):
        ndk_path = self.conf.get("tools.android:ndk_path", default=None)
        if ndk_path:
            return str(ndk_path)
        return os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_ROOT")

    def _android_api_level(self):
        try:
            return int(str(self.settings.os.api_level))
        except Exception:
            return 24

    def _android_linker_name(self, target, api_level):
        if target == "aarch64-linux-android":
            return "aarch64-linux-android{}-clang".format(api_level)
        if target == "armv7-linux-androideabi":
            return "armv7a-linux-androideabi{}-clang".format(api_level)
        if target == "i686-linux-android":
            return "i686-linux-android{}-clang".format(api_level)
        if target == "x86_64-linux-android":
            return "x86_64-linux-android{}-clang".format(api_level)
        raise ConanInvalidConfiguration("Unsupported Android linker target: {}".format(target))

    def _android_ndk_host_tag(self):
        system = platform.system()
        if system == "Darwin":
            return "darwin-x86_64"
        if system == "Linux":
            return "linux-x86_64"
        if system == "Windows":
            return "windows-x86_64"
        raise ConanInvalidConfiguration("Unsupported Android NDK host: {}".format(system))

    def _cargo_command(self):
        if shutil.which("rustup"):
            return "rustup run stable cargo"
        return "cargo"

    def _rustc_path(self):
        if not shutil.which("rustup"):
            return None
        try:
            return subprocess.check_output(["rustup", "which", "rustc"], text=True).strip()
        except Exception:
            return None
