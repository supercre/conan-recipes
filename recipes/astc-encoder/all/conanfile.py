from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, rmdir
import os


class AstcEncoderConan(ConanFile):
    name = "astc-encoder"
    version = "5.3.0"
    license = "Apache-2.0"
    author = "Arm Limited"
    url = "https://github.com/ARM-software/astc-encoder"
    description = "The Arm ASTC Encoder, a compressor for the ASTC image format"
    topics = ("astc", "texture-compression", "image-compression", "graphics")
    
    settings = "os", "compiler", "build_type", "arch"
    
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cli": [True, False],
        "isa": ["native", "none", "avx2", "sse4.1", "sse2", "neon"],
        "decompressor_only": [True, False],
    }
    
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cli": False,
        "isa": "native",
        "decompressor_only": False,
    }
    
    exports_sources = (
        "CMakeLists.txt",
        "Source/*",
        "LICENSE.txt",
        "README.md",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        
        # ISA configuration
        tc.variables["ASTCENC_ISA_NATIVE"] = "ON" if self.options.isa == "native" else "OFF"
        tc.variables["ASTCENC_ISA_NONE"] = "ON" if self.options.isa == "none" else "OFF"
        tc.variables["ASTCENC_ISA_AVX2"] = "ON" if self.options.isa == "avx2" else "OFF"
        tc.variables["ASTCENC_ISA_SSE41"] = "ON" if self.options.isa == "sse4.1" else "OFF"
        tc.variables["ASTCENC_ISA_SSE2"] = "ON" if self.options.isa == "sse2" else "OFF"
        tc.variables["ASTCENC_ISA_NEON"] = "ON" if self.options.isa == "neon" else "OFF"
        
        # Build configuration
        tc.variables["ASTCENC_SHAREDLIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["ASTCENC_CLI"] = "ON" if self.options.with_cli else "OFF"
        tc.variables["ASTCENC_DECOMPRESSOR"] = "ON" if self.options.decompressor_only else "OFF"
        
        # Disable options not needed for package build
        tc.variables["ASTCENC_UNITTEST"] = "OFF"
        tc.variables["ASTCENC_ASAN"] = "OFF"
        tc.variables["ASTCENC_UBSAN"] = "OFF"
        tc.variables["ASTCENC_WERROR"] = "OFF"
        
        # Disable universal build (handled by ISA option)
        tc.variables["ASTCENC_UNIVERSAL_BUILD"] = "OFF"
        
        tc.generate()
        
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Copy license
        copy(self, "LICENSE.txt", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
        
        # Copy public headers
        copy(self, "astcenc.h",
             src=os.path.join(self.source_folder, "Source"),
             dst=os.path.join(self.package_folder, "include"))
        
        # Copy library files
        copy(self, "*.lib",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.so*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.dylib",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.dll",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        
        # Copy CLI executables if enabled
        if self.options.with_cli:
            copy(self, "astcenc*",
                 src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
            copy(self, "astcdec*",
                 src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)

    def package_info(self):
        # Determine suffix based on ISA and codec type
        isa_suffix = str(self.options.isa).replace(".", "")
        codec_suffix = "dec" if self.options.decompressor_only else "enc"
        
        # Library naming follows the pattern: astcenc-{isa} or astcdec-{isa}
        lib_name = f"astc{codec_suffix}-{isa_suffix}"
        
        if self.options.shared:
            lib_name += "-shared"
        else:
            lib_name += "-static"
        
        self.cpp_info.libs = [lib_name]
        
        # Set include directories
        self.cpp_info.includedirs = ["include"]
        
        # Add system libraries based on platform
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "m"])
        elif self.settings.os == "Windows":
            pass  # No additional system libs needed on Windows
        
        # Set CMake target names
        self.cpp_info.set_property("cmake_file_name", "astc-encoder")
        self.cpp_info.set_property("cmake_target_name", "astc-encoder::astc-encoder")
        
        # CLI tool binary info
        if self.options.with_cli:
            bin_name = f"astc{codec_suffix}-{isa_suffix}"
            self.cpp_info.bindirs = ["bin"]

