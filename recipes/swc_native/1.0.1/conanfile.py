import json
from conan import ConanFile
from conan.tools.files import copy
from conan.errors import ConanInvalidConfiguration
import os
import subprocess


class SwcNativeConan(ConanFile):
    name = "swc_native"
    version = "1.0.1"
    user = "sc"
    channel = "dev"
    
    # Metadata
    license = "MIT"
    author = "Supercreative Inc."
    url = "https://github.com/supercre/swc_native"
    description = "SWC TypeScript compiler C FFI wrapper"
    topics = ("typescript", "compiler", "swc", "ffi", "rust")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "fPIC": True
    }
    
    exports_sources = "Cargo.toml", "Cargo.lock", "src/*", "include/*"
    no_copy_source = True

    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def validate(self):
        """플랫폼/아키텍처 호환성 검증"""
        # Windows와 macOS 데스크탑만 지원
        if self.settings.os not in ["Windows", "Macos"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported. Only Windows and macOS are supported.")
        
        # 지원되는 아키텍처 검증
        supported_archs = ["x86_64", "armv8"]
        if self.settings.arch not in supported_archs:
            raise ConanInvalidConfiguration(f"Architecture {self.settings.arch} is not supported. Supported: {supported_archs}")

    def _get_rust_target(self):
        """Rust 타겟 트리플 반환"""
        if self.settings.os == "Windows":
            if self.settings.arch == "x86_64":
                return "x86_64-pc-windows-msvc"
            elif self.settings.arch == "armv8":
                return "aarch64-pc-windows-msvc"
        elif self.settings.os == "Macos":
            if self.settings.arch == "armv8":
                return "aarch64-apple-darwin"
            elif self.settings.arch == "x86_64":
                return "x86_64-apple-darwin"
        return None

    def build(self):
        """Build the Rust library using Cargo"""
        src_folder = self.source_folder
        target = self._get_rust_target()
        
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported platform: {self.settings.os}/{self.settings.arch}")
        
        # Rust 타겟 설치 확인
        self.output.info(f"Ensuring Rust target {target} is installed...")
        subprocess.run(["rustup", "target", "add", target], check=True)
        
        # Build command
        build_type = "release" if self.settings.build_type == "Release" else "debug"
        cmd = ["cargo", "build", "--target", target]
        
        if build_type == "release":
            cmd.append("--release")
        
        # --locked 플래그로 Cargo.lock 사용
        cmd.append("--locked")

        self.output.info(f"Building with command: {' '.join(cmd)}")
        
        # Run cargo build
        subprocess.run(cmd, cwd=src_folder, check=True)

    def package(self):
        """Package the built library and headers"""
        # Copy header files
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

        # Determine library output path
        build_type = "release" if self.settings.build_type == "Release" else "debug"
        target = self._get_rust_target()
        lib_folder = os.path.join(self.source_folder, "target", target, build_type)
        
        # Fallback to non-target folder if target-specific doesn't exist
        if not os.path.exists(lib_folder):
            lib_folder = os.path.join(self.source_folder, "target", build_type)

        self.output.info(f"Copying libraries from: {lib_folder}")

        # Copy libraries based on options
        if self.options.shared:
            # 공유 라이브러리
            if self.settings.os == "Windows":
                copy(self, "swc_native.dll",
                     src=lib_folder,
                     dst=os.path.join(self.package_folder, "bin"))
                copy(self, "swc_native.dll.lib",
                     src=lib_folder,
                     dst=os.path.join(self.package_folder, "lib"))
            else:
                copy(self, "libswc_native.dylib",
                     src=lib_folder,
                     dst=os.path.join(self.package_folder, "lib"))
        else:
            # 정적 라이브러리
            if self.settings.os == "Windows":
                copy(self, "swc_native.lib",
                     src=lib_folder,
                     dst=os.path.join(self.package_folder, "lib"))
            else:
                copy(self, "libswc_native.a",
                     src=lib_folder,
                     dst=os.path.join(self.package_folder, "lib"))

    def compatibility(self):
        """
        패키지 바이너리 호환성 설정
        
        Rust FFI 라이브러리는 C ABI를 사용하므로 C++ 표준(cppstd)이나 
        컴파일러 버전에 영향받지 않습니다.
        이러한 설정이 달라도 동일한 바이너리를 재사용할 수 있습니다.
        """
        return [
            {"settings": [("compiler.cppstd", None)]},
            {"settings": [("compiler.version", None)]},
            {"settings": [("compiler.runtime_type", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None), ("compiler.runtime_type", None)]},
        ]

    def package_id(self):
        """패키지 ID 설정 - build_type과 runtime_type 제외"""
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
        self.output.info(f"{json.dumps(settings_info, indent=4)}")

    def package_info(self):
        """Define package information for consumers"""
        self.cpp_info.libs = ["swc_native"]
        
        # Include directory
        self.cpp_info.includedirs = ["include"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "swc_native")
        
        # CMake 설정
        self.cpp_info.set_property("cmake_file_name", "SwcNative")
        self.cpp_info.set_property("cmake_target_name", "SwcNative::SwcNative")
        
        # Windows-specific system libraries (Rust runtime dependencies)
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = [
                "ws2_32",      # Windows Sockets
                "userenv",     # User environment
                "bcrypt",      # Crypto
                "ntdll",       # NT internals
                "advapi32",    # Advanced Windows API
                "kernel32",    # Windows kernel
                "ole32",       # OLE
                "oleaut32",    # OLE Automation
                "shell32",     # Windows Shell
                "synchronization",  # Sync primitives
            ]
        elif self.settings.os == "Macos":
            self.cpp_info.system_libs = ["c++", "pthread", "dl"]
            self.cpp_info.frameworks = ["Security", "CoreFoundation"]
        
        # 디버깅 정보 출력
        self.output.info(f"SwcNative {self.version} configured with:")
        self.output.info(f"  Rust target: {self._get_rust_target()}")
        self.output.info(f"  Libdirs: {self.cpp_info.libdirs}")
        self.output.info(f"  Includedirs: {self.cpp_info.includedirs}")
