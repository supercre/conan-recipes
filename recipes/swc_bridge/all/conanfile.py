import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy


class SsrSwcBridgeConan(ConanFile):
    name = "swc_bridge"
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
        if self.settings.os not in ("Windows", "Macos", "iOS"):
            raise ConanInvalidConfiguration("swc_bridge is supported only on Windows, macOS, and iOS")

    def build(self):
        manifest = os.path.join(self.source_folder, "Cargo.toml")
        target = self._rust_target()
        cargo, rustc = self._rust_tool_commands(target)
        profile_args = []
        if str(self.settings.build_type).lower() != "debug":
            profile_args.append("--release")

        cargo_env = Environment()
        cargo_env.define("CARGO_TARGET_DIR", os.path.join(self.build_folder, "cargo"))
        if rustc:
            cargo_env.define("RUSTC", rustc)

        with cargo_env.vars(self).apply():
            self.run(
                "{} build --manifest-path \"{}\" --target {} {}".format(
                    cargo,
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
            sdk = self.settings.get_safe("os.sdk") or "iphoneos"
            if arch in ("armv8", "arm64", "armv8.3"):
                if sdk == "iphonesimulator":
                    return "aarch64-apple-ios-sim"
                return "aarch64-apple-ios"
            if arch == "x86_64" and sdk == "iphonesimulator":
                return "x86_64-apple-ios"

        raise ConanInvalidConfiguration("Unsupported Rust target for {} {}".format(os_name, arch))

    def _rust_tool_commands(self, target):
        rustup = shutil.which("rustup")
        if rustup:
            self._ensure_rustup_target(rustup, target)
            try:
                cargo_path = subprocess.check_output(
                    [rustup, "which", "cargo"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                rustc_path = subprocess.check_output(
                    [rustup, "which", "rustc"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                if cargo_path:
                    return "\"{}\"".format(cargo_path), rustc_path or None
            except (OSError, subprocess.SubprocessError):
                pass
        return "cargo", None

    def _ensure_rustup_target(self, rustup, target):
        try:
            installed = subprocess.check_output(
                [rustup, "target", "list", "--installed"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).splitlines()
        except (OSError, subprocess.SubprocessError):
            return
        if target not in installed:
            self.run("\"{}\" target add {}".format(rustup, target))
