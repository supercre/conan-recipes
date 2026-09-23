import json
import shutil
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import get, copy
from conan.tools.scm import Git
from conan.errors import ConanException
import os


class PngConan(ConanFile):
    name = "png"
    version = "1.6.50"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "libpng is the official PNG reference library"
    homepage = "https://github.com/glennrp/libpng"
    license = "PNG"
    topics = ("png", "image", "compression")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "neon": [True, False],
        "msa": [True, False],
        "sse": [True, False],
        "vsx": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "fPIC": True,
        "neon": True,
        "msa": False,
        "sse": True,
        "vsx": False
    }
    
    def requirements(self):
        """종속성 설정"""
        self.requires(f"zlib/[>=1.3]@{self.user}/{self.channel}")
    
    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch in ["armv7"]:
            self.options.neon = False
        if self.settings.arch != "mips":
            del self.options.msa
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.sse
        if self.settings.arch not in ["ppc32", "ppc64le"]:
            del self.options.vsx
    
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def layout(self):
        """디렉토리 레이아웃 설정"""
        cmake_layout(self)
    
    def source(self):
        """소스 코드 다운로드"""
        # Git을 사용하여 libpng 소스 다운로드
        git = Git(self)
        git.clone(url="https://github.com/glennrp/libpng.git",
                  target=self.source_folder,
                  args=["--branch", f"v{self.version}", "--depth", "1"])
    
    def generate(self):
        """빌드 파일 생성"""
        # CMake 툴체인 및 종속성 생성
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["PNG_TESTS"] = False
        tc.variables["PNG_EXECUTABLES"] = False
        tc.variables["PNG_BUILD_ZLIB"] = False  # 외부 zlib 사용
        tc.variables["ZLIB_USE_STATIC_LIBS"] = not self.options.shared
        tc.variables["PNG_SHARED"] = self.options.shared
        tc.variables["PNG_STATIC"] = not self.options.shared
       
        # SIMD 최적화 설정
        if self.options.get_safe("neon"):
            tc.variables["PNG_ARM_NEON"] = "on" if self.options.neon else "off"
        
        if self.options.get_safe("msa"):
            tc.variables["PNG_MIPS_MSA"] = "on" if self.options.msa else "off"
        
        if self.options.get_safe("sse"):
            tc.variables["PNG_INTEL_SSE"] = "on" if self.options.sse else "off"
        
        if self.options.get_safe("vsx"):
            tc.variables["PNG_POWERPC_VSX"] = "on" if self.options.vsx else "off"
        
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
            tc.variables["PNG_FRAMEWORK"] = False
            developer_dir = os.environ.get('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
            if not os.path.exists(developer_dir):
                raise ConanException(f"Xcode Developer directory not found: {developer_dir}")
            
            deployment_target = os.environ.get('IPHONEOS_DEPLOYMENT_TARGET', '13.0')
            tc.variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = deployment_target
            ios_sdk = str(self.settings.get_safe("os.sdk", "iphoneos"))
            
            if self.settings.arch == "armv8" and ios_sdk == "iphonesimulator":
                sdk_path = f"{developer_dir}/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
            elif self.settings.arch == "armv8":
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

        lib_dir = os.path.join(self.package_folder, "lib")
        debug_png = os.path.join(lib_dir, "libpng16d.a")
        alias_png = os.path.join(lib_dir, "libpng16.a")
        if os.path.exists(debug_png) and not os.path.exists(alias_png):
            shutil.copyfile(debug_png, alias_png)
        
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
        if self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.libs = ["libpng16"]
            else:
                self.cpp_info.libs = ["libpng16_static"]
        else:
            self.cpp_info.libs = ["png16"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "libpng16")
        
        # CMake 타겟 설정
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "PNG")
        self.cpp_info.set_property("cmake_target_name", "PNG::PNG")
