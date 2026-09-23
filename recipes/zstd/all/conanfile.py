#!/usr/bin/env python3
"""
Conan recipe for Zstandard (zstd)
Zstandard is a real-time compression algorithm
"""

import json
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, rmdir
from conan.tools.scm import Git
import os

class ZstdConan(ConanFile):
    name = "zstd"
    version = "1.5.7"
    user = "sc"
    channel = "dev"
    description = "Zstandard is a real-time compression algorithm"
    license = "BSD-3-Clause"
    url = "https://github.com/facebook/zstd"
    homepage = "https://facebook.github.io/zstd/"
    topics = ("compression", "lossless", "algorithm", "zstandard")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threading": [True, False],
        "zlib": [True, False],
        "lz4": [True, False],
        "lzma": [True, False],
        "program": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threading": True,
        "zlib": False,
        "lz4": False,
        "lzma": False,
        "program": False,
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
        git.clone(url="https://github.com/facebook/zstd.git",
                  target=self.source_folder,
                  args=["--branch", f"v{self.version}", "--depth", "1"])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["ZSTD_BUILD_SHARED"] = self.options.shared
        tc.variables["ZSTD_BUILD_STATIC"] = not self.options.shared
        tc.variables["ZSTD_PROGRAMS_LINK_SHARED"] = self.options.shared
        tc.variables["ZSTD_BUILD_TESTS"] = False
        tc.variables["ZSTD_BUILD_PROGRAMS"] = self.options.program
        tc.variables["ZSTD_LEGACY_SUPPORT"] = True
        tc.variables["ZSTD_BUILD_CONTRIB"] = False
        tc.variables["ZSTD_MULTITHREAD_SUPPORT"] = self.options.threading
        tc.variables["ZSTD_ZLIB_SUPPORT"] = self.options.zlib
        tc.variables["ZSTD_LZ4_SUPPORT"] = self.options.lz4
        tc.variables["ZSTD_LZMA_SUPPORT"] = self.options.lzma
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        
        # iOS 특별 설정
        if self.settings.os == "iOS":
            # iOS에서 Bundle 생성 비활성화
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False
            # iOS에서 정적 라이브러리 강제 설정
            tc.variables["ZSTD_BUILD_SHARED"] = False
            tc.variables["ZSTD_BUILD_STATIC"] = True
            tc.variables["BUILD_SHARED_LIBS"] = False
        
        # macOS 특별 설정
        elif self.settings.os == "Macos":
            # macOS에서 Bundle 생성 비활성화
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False
        
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        # build/cmake 폴더를 소스 디렉토리로 지정
        cmake.configure(build_script_folder="build/cmake")
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
        self.cpp_info.set_property("cmake_file_name", "ZSTD")
        self.cpp_info.set_property("cmake_target_name", "ZSTD::zstd")
        self.cpp_info.set_property("pkg_config_name", "libzstd")
        
        # Libraries
        if self.options.shared:
            self.cpp_info.libs = ["zstd"]
        else:
            if self.settings.os == "Windows":
                self.cpp_info.libs = ["zstd_static"]
            else:
                self.cpp_info.libs = ["zstd"]
        
        # Include directories
        self.cpp_info.includedirs = ["include"]
        
        # Define ZSTD_DLL_IMPORT if shared
        if self.options.shared:
            self.cpp_info.defines.append("ZSTD_DLL_IMPORT")
        
        # Additional libraries for static builds
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("pthread")
            elif self.settings.os == "Windows":
                self.cpp_info.system_libs.append("winmm")
