#!/usr/bin/env python3
"""
Conan recipe for Brotli
Brotli is a generic-purpose lossless compression algorithm
"""

import json
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, rmdir
from conan.tools.scm import Git
import os

class BrotliConan(ConanFile):
    name = "brotli"
    version = "1.1.0"
    user = "sc"
    channel = "dev"
    description = "Brotli is a generic-purpose lossless compression algorithm"
    license = "MIT"
    url = "https://github.com/google/brotli"
    homepage = "https://brotli.org/"
    topics = ("compression", "lossless", "algorithm")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        git = Git(self)
        git.clone(url="https://github.com/google/brotli.git",
                  target=self.source_folder,
                  args=["--branch", f"v{self.version}", "--depth", "1"])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BROTLI_BUNDLED_MODE"] = False
        tc.variables["BROTLI_DISABLE_TESTS"] = True
        tc.variables["BROTLI_DISABLE_CLI"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared

        if self.settings.os == "Macos":
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False
            tc.variables["BROTLI_BUILD_TOOLS"] = False
        elif self.settings.os == "iOS":
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False
            tc.variables["BROTLI_BUILD_TOOLS"] = False

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        
        # Copy license
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        
        # Remove CMake config files
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def compatibility(self):
        """
        패키지 바이너리 호환성 설정
        
        순수 C 라이브러리는 C++ 표준(cppstd)이나 컴파일러 버전에 영향받지 않으므로,
        이러한 설정이 달라도 동일한 바이너리를 재사용할 수 있습니다.
        예: cppstd=20으로 빌드된 패키지를 cppstd=14 환경에서도 사용 가능.
        """
        return [
            {"settings": [("compiler.cppstd", None)]},
            {"settings": [("compiler.version", None)]},
            {"settings": [("compiler.runtime_type", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None), ("compiler.runtime_type", None)]},
        ]

    def package_id(self):
        del self.info.settings.build_type
        try:
            del self.info.settings.compiler.runtime_type
        except Exception:
            pass
        settings_info = {
            "os": str(self.info.settings.os),
            "arch": str(self.info.settings.arch),
            "compiler": str(self.info.settings.compiler)
        }
        self.output.info(f"{json.dumps(settings_info,indent=4)}")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Brotli")
        self.cpp_info.set_property("cmake_target_name", "Brotli::brotli")
        self.cpp_info.set_property("pkg_config_name", "libbrotli")
        
        # Libraries - Brotli는 3개의 라이브러리로 구성됨
        self.cpp_info.libs = ["brotlienc", "brotlidec", "brotlicommon"]
        
        # Include directories - brotli 헤더는 include/brotli/ 디렉토리에 있음
        self.cpp_info.includedirs = ["include"]
        
        # Define BROTLI_SHARED_COMPILATION if shared
        if self.options.shared:
            self.cpp_info.defines.append("BROTLI_SHARED_COMPILATION")
        
        # Set target properties for CMake
        self.cpp_info.set_property("cmake_target_name", "Brotli::brotli")
        
        # Additional libraries for static builds
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("m")
