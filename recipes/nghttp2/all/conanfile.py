import json
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git
from conan.errors import ConanException
import os


class Nghttp2Conan(ConanFile):
    name = "nghttp2"
    version = "1.66.0"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "HTTP/2 C library and tools"
    homepage = "https://github.com/nghttp2/nghttp2"
    license = "MIT"
    topics = ("http2", "http", "networking", "protocol")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "static": [True, False],
        "fPIC": [True, False],
        "with_asio": [True, False],
        "with_app": [True, False],
        "with_hpack": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "static": True,
        "fPIC": True,
        "with_asio": False,
        "with_app": False,
        "with_hpack": True
    }
    
    def requirements(self):
        """의존성 설정"""
        self.requires(f"zlib/[^1.3.0]@{self.user}/{self.channel}")            
        self.requires(f"openssl/[^3.5.0]@{self.user}/{self.channel}")            

    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def layout(self):
        """디렉토리 레이아웃 설정"""
        cmake_layout(self)
    
    def source(self):
        """소스 코드 다운로드 (서브모듈 포함)"""
        git = Git(self)
        git.clone(url="https://github.com/nghttp2/nghttp2.git",
                  target=self.source_folder,
                  args=["--branch", f"v{self.version}", "--depth", "1", "--recurse-submodules"])
    
    def generate(self):
        """빌드 파일 생성"""
        # CMake 툴체인 및 종속성 생성
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = self.options.static        
        tc.variables["ENABLE_LIB_ONLY"] = True
        tc.variables["ENABLE_STATIC_LIB"] = self.options.static #True #not self.options.shared
        tc.variables["ENABLE_ASIO_LIB"] = self.options.with_asio
        tc.variables["ENABLE_APP"] = self.options.with_app
        tc.variables["ENABLE_HPACK_TOOLS"] = self.options.with_hpack
        
        # Android 특별 설정
        if self.settings.os == "Android":
            android_ndk = os.environ.get('ANDROID_NDK_HOME') or os.environ.get('ANDROID_NDK_ROOT')
            if not android_ndk:
                raise ConanException("ANDROID_NDK_HOME environment variable not set!")
            
            tc.variables["CMAKE_TOOLCHAIN_FILE"] = f"{android_ndk}/build/cmake/android.toolchain.cmake"
            tc.variables["ANDROID_NDK"] = android_ndk
            tc.variables["ANDROID_PLATFORM"] = "android-24"
            
            if self.settings.arch == "armv8":
                tc.variables["ANDROID_ABI"] = "arm64-v8a"
            elif self.settings.arch == "armv7":
                tc.variables["ANDROID_ABI"] = "armeabi-v7a"
            elif self.settings.arch == "x86_64":
                tc.variables["ANDROID_ABI"] = "x86_64"
            elif self.settings.arch == "x86":
                tc.variables["ANDROID_ABI"] = "x86"
        
        # iOS 특별 설정
        elif self.settings.os == "iOS":
            developer_dir = os.environ.get('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
            if not os.path.exists(developer_dir):
                raise ConanException(f"Xcode Developer directory not found: {developer_dir}")
            
            deployment_target = os.environ.get('IPHONEOS_DEPLOYMENT_TARGET', '13.0')
            tc.variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = deployment_target
            
            if self.settings.arch == "armv8":
                sdk_path = f"{developer_dir}/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
            elif self.settings.arch == "x86_64":
                sdk_path = f"{developer_dir}/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "x86_64"
            
            tc.variables["CMAKE_C_FLAGS"] = f"-mios-version-min={deployment_target}"
            tc.variables["CMAKE_CXX_FLAGS"] = f"-mios-version-min={deployment_target}"
        
        # macOS 특별 설정
        elif self.settings.os == "Macos":
            developer_dir = os.environ.get('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
            deployment_target = os.environ.get('MACOSX_DEPLOYMENT_TARGET', '11.0')
            tc.variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = deployment_target
            
            if self.settings.arch == "armv8":
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif self.settings.arch == "x86_64":
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "x86_64"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
                
        tc.generate()
        
        deps = CMakeDeps(self)
        deps.generate()
    
    def build(self):
        """패키지 빌드"""
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    def package(self):
        """패키지 파일 복사"""
        cmake = CMake(self)
        cmake.install()
        
        # 라이선스 파일 복사
        copy(self, "COPYING", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
    
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
        """패키지 정보 설정"""
        self.cpp_info.libs = ["nghttp2"]
        # Windows 시스템 라이브러리 링크
        if self.settings.os == "Windows":
            system_libs = ["ws2_32"]
            existing = list(getattr(self.cpp_info, "system_libs", []) or [])
            self.cpp_info.system_libs = existing + system_libs
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "libnghttp2")
        
        # CMake 타겟 설정
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "nghttp2")
        self.cpp_info.set_property("cmake_target_name", "nghttp2::nghttp2")
