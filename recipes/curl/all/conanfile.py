import json
import shutil
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git
from conan.errors import ConanException
import os


class CurlConan(ConanFile):
    name = "curl"
    version = "8.15.0"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "Command line tool and library for transferring data with URLs"
    homepage = "https://github.com/curl/curl"
    license = "MIT"
    topics = ("http", "https", "ftp", "networking", "curl")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
        
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_ssh": [True, False],
        "with_openssl": [True, False],
        "with_zlib": [True, False],
        "with_nghttp2": [True, False],
        "with_nghttp3": [True, False],  # HTTP/3 프로토콜 계층
        "with_zstd": [True, False],     # Zstandard 압축 지원
        "with_brotli": [True, False],   # Brotli 압축 지원
        "with_quic": [True, False],     # OpenSSL 3.5.2+ 내장 QUIC 사용
        "with_c_ares": [True, False],
        "with_libidn2": [True, False],  # 국제화 도메인명 지원
        "with_libpsl": [True, False],    # Public Suffix List 지원
        "with_ntlm": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "fPIC": True,
        "with_ssl": True,
        "with_ssh": False,
        "with_openssl": True,
        "with_zlib": True,
        "with_nghttp2": True,
        "with_nghttp3": True,   # HTTP/3 지원 기본 활성화
        "with_zstd": True,      # Zstandard 압축 지원 기본 활성화
        "with_brotli": True,    # Brotli 압축 지원 기본 활성화
        "with_quic": True,      # OpenSSL 3.5.2+ 내장 QUIC 기본 활성화
        "with_c_ares": False,
        "with_libidn2": False,  # 기본 비활성화 (필요시 활성화)
        "with_libpsl": False,    # 기본 비활성화 (필요시 활성화)
        "with_ntlm": False
    }
    
    def requirements(self):
        """종속성 설정"""
        if self.options.with_openssl:
            # OpenSSL 3.5.2 이상에서 내장 QUIC 지원
            self.requires(f"openssl/[>=3.5.2 <4]@{self.user}/{self.channel}")
        if self.options.with_nghttp2:
            self.requires(f"nghttp2/[>=1.59.0 <2]@{self.user}/{self.channel}")
        if self.options.with_nghttp3:
            self.requires(f"nghttp3/[>=1.11.0 <2]@{self.user}/{self.channel}")  # HTTP/3 프로토콜 계층
        if self.options.with_zstd:
            self.requires(f"zstd/[>=1.5.5 <2]@{self.user}/{self.channel}")
        if self.options.with_brotli:
            self.requires(f"brotli/[>=1.1.0 <2]@{self.user}/{self.channel}")
        if self.options.with_zlib:
            self.requires(f"zlib/[>=1.2.11 <2]@{self.user}/{self.channel}")
        if self.options.with_c_ares:
            self.requires(f"c-ares/[>=1.27 <2]@{self.user}/{self.channel}")
        if self.options.with_libidn2:
            self.requires(f"libidn2/[>=2.3.0 <3]@{self.user}/{self.channel}")
        if self.options.with_libpsl:
            self.requires(f"libpsl/[>=0.21.0 <1]@{self.user}/{self.channel}")
        if self.options.with_ntlm:
            self.requires(f"libntlm/[>=1.3 <2]@{self.user}/{self.channel}")
    
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
        
        # OpenSSL이 zstd/brotli 지원을 사용하지 않도록 설정하여 try_compile 문제 방지
        if self.options.with_openssl:
            self.options["openssl"].zstd = False
            self.options["openssl"].brotli = False

    
    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def layout(self):
        """디렉토리 레이아웃 설정"""
        cmake_layout(self)
        self.folders.source = "src"
    
    def source(self):
        """소스 코드 다운로드 (서브모듈 포함)"""
        git = Git(self)
        git.clone(url="https://github.com/curl/curl.git",
                  target=self.source_folder,
                  args=["--branch", f"curl-{self.version.replace('.', '_')}", "--depth", "1", "--recurse-submodules"])
    
    def generate(self):
        """빌드 파일 생성"""
        # CMake 툴체인 및 종속성 생성
        tc = CMakeToolchain(self)

        # try_compile에도 Conan deps/설정이 전파되도록
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        
        # try_compile에서 의존성을 찾을 수 있도록 패키지 설정 전파
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        
        # OpenSSL의 OPENSSL_IS_BORINGSSL 체크를 스킵하도록 설정 (try_compile 문제 해결)
        tc.cache_variables["OPENSSL_IS_BORINGSSL"] = "FALSE"
        tc.cache_variables["HAVE_OPENSSL_IS_BORINGSSL"] = "FALSE"
        
        # CheckSymbolExists에서 try_compile 문제를 피하기 위해 미리 정의
        tc.cache_variables["CMAKE_CROSSCOMPILING"] = "FALSE"
        
        # Zstd와 Brotli를 try_compile에서 찾을 수 있도록 설정
        if self.options.with_zstd:
            zstd_root = self.dependencies["zstd"].package_folder.replace('\\', '/')
            tc.cache_variables["ZSTD_FOUND"] = "TRUE"
            tc.cache_variables["ZSTD_INCLUDE_DIR"] = f"{zstd_root}/include"
            tc.cache_variables["ZSTD_LIBRARIES"] = f"{zstd_root}/lib"
            tc.cache_variables["ZSTD_ROOT"] = zstd_root
        
        if self.options.with_brotli:
            brotli_root = self.dependencies["brotli"].package_folder.replace('\\', '/')
            tc.cache_variables["BROTLI_FOUND"] = "TRUE"
            tc.cache_variables["BROTLI_INCLUDE_DIRS"] = f"{brotli_root}/include"
            tc.cache_variables["BROTLI_LIBRARIES"] = f"{brotli_root}/lib"
            tc.cache_variables["BROTLI_ROOT"] = brotli_root

        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        # (선택) 시스템 패키지 레지스트리 차단
        tc.variables["CMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY"] = True
        tc.variables["CMAKE_FIND_PACKAGE_NO_SYSTEM_PACKAGE_REGISTRY"] = True

        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_CURL_EXE"] = False
        tc.variables["BUILD_TESTING"] = False
        
        # OpenSSL 설정
        if self.options.with_openssl:
            tc.variables["CURL_USE_OPENSSL"] = True
            tc.variables["OPENSSL_USE_STATIC_LIBS"] = not self.options.shared
        else:
            tc.variables["CURL_USE_OPENSSL"] = False
        
        tc.variables["CURL_USE_LIBSSH2"] = self.options.with_ssh
        tc.variables["CURL_ZLIB"] = self.options.with_zlib
        tc.variables["ZLIB_USE_STATIC_LIBS"] = not self.options.shared
        tc.variables["USE_NGHTTP2"] = self.options.with_nghttp2
        tc.variables["USE_NGHTTP3"] = self.options.with_nghttp3
        tc.variables["USE_NGTCP2"] = False  # OpenSSL 3.5.2+ 내장 QUIC 사용
        tc.variables["ENABLE_ARES"] = self.options.with_c_ares
        tc.variables["USE_LIBIDN2"] = self.options.with_libidn2
        tc.variables["CURL_USE_LIBPSL"] = self.options.with_libpsl
        tc.variables["CURL_BROTLI"] = self.options.with_brotli
        tc.variables["CURL_ZSTD"] = self.options.with_zstd
        tc.variables["CURL_DISABLE_NTLM"] = not self.options.with_ntlm
        
        # Find package 설정 활성화
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        
        # nghttp2/nghttp3 경로를 직접 설정하여 curl의 FindNGHTTP2.cmake 모듈이 찾을 수 있도록 함
        if self.options.with_nghttp2:
            nghttp2_root = self.dependencies["nghttp2"].package_folder.replace('\\', '/')
            nghttp2_include = f"{nghttp2_root}/include"
            nghttp2_lib = f"{nghttp2_root}/lib/nghttp2.lib" if self.settings.os == "Windows" else f"{nghttp2_root}/lib/libnghttp2.a"

            tc.variables["NGHTTP2_INCLUDE_DIR"] = nghttp2_include
            tc.variables["NGHTTP2_LIBRARY"] = nghttp2_lib
            # 복수형도 설정하여 확실하게 함
            tc.variables["NGHTTP2_INCLUDE_DIRS"] = nghttp2_include
            tc.variables["NGHTTP2_LIBRARIES"] = nghttp2_lib
            tc.variables["NGHTTP2_FOUND"] = True
            tc.variables["NGHTTP2_STATICLIB"] = True
            
            # 정적 라이브러리 매크로를 컴파일러 정의로 추가
            tc.cache_variables["NGHTTP2_STATICLIB"] = True
            tc.preprocessor_definitions["NGHTTP2_STATICLIB"] = "1"

            self.output.info(f"NGHTTP2 설정:")
            self.output.info(f"  Include: {nghttp2_include}")
            self.output.info(f"  Library: {nghttp2_lib}")
        
        if self.options.with_nghttp3:
            nghttp3_root = self.dependencies["nghttp3"].package_folder.replace('\\', '/')
            nghttp3_include = f"{nghttp3_root}/include"
            nghttp3_lib = f"{nghttp3_root}/lib/nghttp3.lib" if self.settings.os == "Windows" else f"{nghttp3_root}/lib/libnghttp3.a"
            
            tc.variables["NGHTTP3_INCLUDE_DIR"] = nghttp3_include  
            tc.variables["NGHTTP3_LIBRARY"] = nghttp3_lib
            # 복수형도 설정
            tc.variables["NGHTTP3_INCLUDE_DIRS"] = nghttp3_include
            tc.variables["NGHTTP3_LIBRARIES"] = nghttp3_lib
            tc.variables["NGHTTP3_FOUND"] = True
            tc.variables["NGHTTP3_STATICLIB"] = True
            
            # 정적 라이브러리 매크로를 컴파일러 정의로 추가  
            tc.cache_variables["NGHTTP3_STATICLIB"] = True
            tc.preprocessor_definitions["NGHTTP3_STATICLIB"] = "1"
            
            self.output.info(f"NGHTTP3 설정:")
            self.output.info(f"  Include: {nghttp3_include}")
            self.output.info(f"  Library: {nghttp3_lib}")

        if self.options.with_zstd:
            zstd_root = self.dependencies["zstd"].package_folder.replace('\\', '/')
            zstd_include = f"{zstd_root}/include"
            zstd_lib = f"{zstd_root}/lib/zstd.lib" if self.settings.os == "Windows" else f"{zstd_root}/lib/libzstd.a"
            
            tc.variables["ZSTD_INCLUDE_DIR"] = zstd_include
            tc.variables["ZSTD_LIBRARIES"] = zstd_lib
            tc.variables["ZSTD_FOUND"] = True
            tc.variables["ZSTD_ROOT"] = zstd_root
            
            # try_compile에서도 사용할 수 있도록 추가 설정
            tc.cache_variables["ZSTD_INCLUDE_DIR"] = zstd_include
            tc.cache_variables["ZSTD_LIBRARIES"] = zstd_lib
            
            self.output.info(f"ZSTD 설정:")
            self.output.info(f"  Include: {zstd_include}")
            self.output.info(f"  Library: {zstd_lib}")
        
        if self.options.with_brotli:
            brotli_root = self.dependencies["brotli"].package_folder.replace('\\', '/')
            brotli_include = f"{brotli_root}/include"
            # Brotli는 3개의 라이브러리로 구성됨
            if self.settings.os == "Windows":
                brotli_libs = [
                    f"{brotli_root}/lib/brotlienc.lib",
                    f"{brotli_root}/lib/brotlidec.lib", 
                    f"{brotli_root}/lib/brotlicommon.lib"
                ]
            else:
                brotli_libs = [
                    f"{brotli_root}/lib/libbrotlienc.a",
                    f"{brotli_root}/lib/libbrotlidec.a",
                    f"{brotli_root}/lib/libbrotlicommon.a"
                ]
            
            tc.variables["BROTLI_INCLUDE_DIRS"] = brotli_include
            tc.variables["BROTLI_LIBRARIES"] = ";".join(brotli_libs)
            tc.variables["BROTLI_FOUND"] = True
            tc.variables["BROTLI_ROOT"] = brotli_root
            
            # try_compile에서도 사용할 수 있도록 추가 설정
            tc.cache_variables["BROTLI_INCLUDE_DIRS"] = brotli_include
            tc.cache_variables["BROTLI_LIBRARIES"] = ";".join(brotli_libs)
            
            self.output.info(f"BROTLI 설정:")
            self.output.info(f"  Include: {brotli_include}")
            self.output.info(f"  Libraries: {brotli_libs}")
        
        # OpenSSL 3.5.2+ 내장 QUIC 설정
        if self.options.with_quic and self.options.with_openssl:
            tc.variables["ENABLE_QUIC"] = True
            tc.variables["USE_OPENSSL_QUIC"] = True
        else:
            tc.variables["ENABLE_QUIC"] = False
            tc.variables["USE_OPENSSL_QUIC"] = False
        
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
            ios_sdk = str(self.settings.get_safe("os.sdk", "iphoneos"))
            
            if self.settings.arch == "armv8" and ios_sdk == "iphonesimulator":
                sdk_path = f"{developer_dir}/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
                tc.variables["CMAKE_OSX_SYSROOT"] = sdk_path
                tc.variables["CMAKE_SYSTEM_NAME"] = "iOS"
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.variables["CMAKE_OSX_ARCHITECTURES"] = "arm64"
                # curl's pipe2 probe links successfully on the simulator SDK, but the
                # public headers do not declare it for normal app builds.
                tc.cache_variables["HAVE_PIPE2"] = "0"
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
        
        # Zstd CMake 타겟 설정 - try_compile에서도 사용할 수 있도록
        if self.options.with_zstd:
            deps.set_property("zstd", "cmake_file_name", "ZSTD")
            deps.set_property("zstd", "cmake_target_name", "ZSTD::zstd")
            deps.set_property("zstd", "cmake_build_modules", [])
        
        # Brotli CMake 타겟 설정 - try_compile에서도 사용할 수 있도록
        if self.options.with_brotli:
            deps.set_property("brotli", "cmake_file_name", "Brotli")
            deps.set_property("brotli", "cmake_target_name", "Brotli::brotli")
            deps.set_property("brotli", "cmake_build_modules", [])
        
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

        # iOS simulator Debug builds install libcurl-d.a while existing consumers
        # link against -lcurl. Provide the canonical name as an alias.
        lib_dir = os.path.join(self.package_folder, "lib")
        debug_lib = os.path.join(lib_dir, "libcurl-d.a")
        canonical_lib = os.path.join(lib_dir, "libcurl.a")
        if os.path.exists(debug_lib) and not os.path.exists(canonical_lib):
            shutil.copyfile(debug_lib, canonical_lib)
        
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
        self.cpp_info.libs = ["curl"]
        
        # 정적 라이브러리 매크로 정의
        if self.options.with_nghttp2:
            self.cpp_info.defines.append("NGHTTP2_STATICLIB")
        if self.options.with_nghttp3:
            self.cpp_info.defines.append("NGHTTP3_STATICLIB")
        
        # Windows 시스템 라이브러리
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "wldap32", "crypt32", "advapi32"]
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["SystemConfiguration", "Security", "CoreFoundation"]
            self.cpp_info.system_libs = ["ldap"]
        elif self.settings.os == "Linux":
            self.cpp_info.system_libs = ["rt", "pthread"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "libcurl")
        
        # CMake 타겟 설정
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "CURL")
        self.cpp_info.set_property("cmake_target_name", "CURL::libcurl")
        
        # 의존성 설정
        if self.options.with_openssl:
            self.cpp_info.requires.append("openssl::openssl")
        if self.options.with_nghttp2:
            self.cpp_info.requires.append("nghttp2::nghttp2")
        if self.options.with_nghttp3:
            self.cpp_info.requires.append("nghttp3::nghttp3")
        if self.options.with_zstd:
            self.cpp_info.requires.append("zstd::zstd")
        if self.options.with_brotli:
            self.cpp_info.requires.append("brotli::brotli")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib::zlib")
        if self.options.with_c_ares:
            self.cpp_info.requires.append("c-ares::c-ares")
        if self.options.with_libidn2:
            self.cpp_info.requires.append("libidn2::libidn2")
        if self.options.with_libpsl:
            self.cpp_info.requires.append("libpsl::libpsl")
