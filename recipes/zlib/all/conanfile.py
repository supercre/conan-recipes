import json
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import get, copy
from conan.errors import ConanException
import os


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.1"
    user = "sc"
    channel = "dev"
    
    # Metadata
    description = "zlib compression library (static compilation)"
    homepage = "https://github.com/madler/zlib"
    license = "Zlib"
    topics = ("compression", "zlib", "static")
    
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
        self.folders.source = "src"
        self.folders.build = "build"
    
    def source(self):
        """소스 코드 다운로드"""
        # GitHub에서 zlib 소스 다운로드
        get(self, 
            f"https://github.com/madler/zlib/archive/refs/tags/v{self.version}.tar.gz",
            destination=self.source_folder,
            strip_root=True)
    
    def generate(self):
        """빌드 파일 생성"""
        # CMake 툴체인 및 종속성 생성
        tc = CMakeToolchain(self)
        tc.variables["ZLIB_BUILD_EXAMPLES"] = False
        tc.variables["ZLIB_ENABLE_TESTS"] = False
        tc.variables["SKIP_INSTALL_ALL"] = False
        tc.variables["SKIP_INSTALL_LIBRARIES"] = True
        tc.variables["SKIP_INSTALL_HEADERS"] = False
        tc.variables["SKIP_INSTALL_FILES"] = False
        tc.variables["INSTALL_LIB_DIR"] = "lib"
        tc.variables["INSTALL_INC_DIR"] = "include"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        
        # Android 특별 설정
        if self.settings.os == "Android":
            # Android NDK 환경변수 확인 (두 가지 모두 지원)
            android_ndk = os.environ.get('ANDROID_NDK_ROOT') or os.environ.get('ANDROID_NDK_HOME')
            if not android_ndk:
                raise ConanException("ANDROID_NDK_ROOT or ANDROID_NDK_HOME environment variable not set!")
            
            # Android NDK 툴체인 설정
            tc.variables["CMAKE_TOOLCHAIN_FILE"] = f"{android_ndk}/build/cmake/android.toolchain.cmake"
            tc.variables["ANDROID_NDK"] = android_ndk
            tc.variables["ANDROID_PLATFORM"] = "android-24"  # 최소 API 레벨
            
            # 아키텍처별 ABI 설정
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
            # Xcode Developer 디렉토리 확인
            developer_dir = os.environ.get('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
            if not os.path.exists(developer_dir):
                raise ConanException(f"Xcode Developer directory not found: {developer_dir}")
            
            # iOS 디플로이먼트 타겟 설정
            deployment_target = os.environ.get('IPHONEOS_DEPLOYMENT_TARGET', '13.0')
            tc.variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = deployment_target
            
            # iOS에서 Bundle 생성 비활성화
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False
            
            # 아키텍처별 SDK 및 시스템 설정
            if self.settings.arch == "armv8":
                # iOS 디바이스 (ARM64)
                sdk_path = f"{developer_dir}/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
            elif self.settings.arch == "x86_64":
                # iOS 시뮬레이터 (x86_64)
                sdk_path = f"{developer_dir}/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "x86_64"
            
            # iOS 전용 컴파일러 플래그 (기존 플래그에 추가)
            existing_cflags = tc.variables.get("CMAKE_C_FLAGS", "")
            tc.variables["CMAKE_C_FLAGS"] = (existing_cflags + f" -mios-version-min={deployment_target}").strip()
            existing_cxxflags = tc.variables.get("CMAKE_CXX_FLAGS", "")
            tc.variables["CMAKE_CXX_FLAGS"] = (existing_cxxflags + f" -mios-version-min={deployment_target}").strip()
        
        # macOS 특별 설정
        elif self.settings.os == "Macos":
            # Xcode Developer 디렉토리 확인
            developer_dir = os.environ.get('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
            if not os.path.exists(developer_dir):
                raise ConanException(f"Xcode Developer directory not found: {developer_dir}")
            
            # macOS 디플로이먼트 타겟 설정
            deployment_target = os.environ.get('MACOSX_DEPLOYMENT_TARGET', '11.0')
            tc.variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = deployment_target
            
            # macOS SDK 설정
            sdk_path = f"{developer_dir}/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
            tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
            tc.variables["CMAKE_SYSTEM_NAME"] = "Darwin"
            
            # 아키텍처 설정
            if self.settings.arch == "armv8":
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif self.settings.arch == "x86_64":
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "x86_64"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
            
            # macOS 전용 컴파일러 플래그 (기존 플래그에 추가)
            existing_cflags = tc.variables.get("CMAKE_C_FLAGS", "")
            tc.variables["CMAKE_C_FLAGS"] = (existing_cflags + f" -mmacosx-version-min={deployment_target}").strip()
            existing_cxxflags = tc.variables.get("CMAKE_CXX_FLAGS", "")
            tc.variables["CMAKE_CXX_FLAGS"] = (existing_cxxflags + f" -mmacosx-version-min={deployment_target}").strip()
        
        # 공통: 대용량 파일 지원 (기존 플래그에 추가)
        existing_cflags = tc.variables.get("CMAKE_C_FLAGS", "")
        tc.variables["CMAKE_C_FLAGS"] = (existing_cflags + " -D_LARGEFILE64_SOURCE=1").strip()

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

        # shared 옵션에 따라 라이브러리 복사
        self.output.info(f"Packaging libraries, {self.build_folder}")
        package_lib_dir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # 공유 라이브러리만 복사
            copy(self, "*.dylib", src=self.build_folder, dst=package_lib_dir, keep_path=False)
            copy(self, "*.so*", src=self.build_folder, dst=package_lib_dir, keep_path=False)
            copy(self, "*.dll", src=self.build_folder, dst=package_lib_dir, keep_path=False)
        else:
            # 정적 라이브러리만 복사
            copy(self, "*.a", src=self.build_folder, dst=package_lib_dir, keep_path=False)
            copy(self, "*.lib", src=self.build_folder, dst=package_lib_dir, keep_path=False)

        # 라이선스 파일 복사
        copy(self, "LICENSE", 
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
        # 라이브러리 이름 설정 (CMake에서 생성되는 실제 이름 사용)
        if self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.libs = ["zlib"]
            else:
                # Windows에서 정적 라이브러리는 zlibstatic
                self.cpp_info.libs = ["zlibstatic"]
        else:
            self.cpp_info.libs = ["z"]
        
        # Windows에서 정적 링크 시 시스템 라이브러리 추가
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.system_libs = ["ws2_32"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "zlib")
        
        # CMake 타겟 설정 (deprecated된 cmake_find_mode 제거)
        self.cpp_info.set_property("cmake_file_name", "ZLIB")
        self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
        # CMake에서 Release 라이브러리 경로 지정
        self.cpp_info.set_property("cmake_target_aliases", ["ZLIB"])


        # 디버깅 정보 출력
        self.output.info(f"ZLIB {self.version} configured with:")
        self.output.info(f"  Libdirs: {self.cpp_info.libdirs}")
        self.output.info(f"  Includedirs: {self.cpp_info.includedirs}")
        self.output.info(f"  Packagefolder: {self.package_folder}")
        