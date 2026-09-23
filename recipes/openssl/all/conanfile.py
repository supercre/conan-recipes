import json
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os, XCRun
from conan.tools.build import build_jobs
from conan.tools.files import copy, save, chdir, get, replace_in_file, rm, rmdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, unix_path
from conan.tools.scm import Git, Version
from conan.tools.env import Environment
import os
import platform
import textwrap
import fnmatch

required_conan_version = ">=1.57.0"


class OpensslConan(ConanFile):
    name = "openssl"
    version = "3.5.2"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "A toolkit for the Transport Layer Security (TLS) and Secure Sockets Layer (SSL) protocols"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/openssl/openssl"
    license = "Apache-2.0"
    topics = ("ssl", "tls", "encryption", "security")
    package_type = "library"
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # 보안 기능
        "enable_fips": [True, False],
        "weak_ssl_ciphers": [True, False],
        # 프로토콜 지원
        "ssl3": [True, False],
        "tls1": [True, False],
        "tls1_1": [True, False],
        "dtls1": [True, False],
        # 압축 지원
        "zlib": [True, False],
        "brotli": [True, False],
        "zstd": [True, False],
        # 알고리즘 지원
        "rc2": [True, False],
        "rc4": [True, False],
        "rc5": [True, False],
        "md2": [True, False],
        "md4": [True, False],
        "mdc2": [True, False],
        "rmd160": [True, False],
        "idea": [True, False],
        "des": [True, False],
        "bf": [True, False],
        "cast": [True, False],
        "seed": [True, False],
        "gost": [True, False],
        "sm2": [True, False],
        "sm3": [True, False],
        "sm4": [True, False],
        # 기능 모듈
        "cms": [True, False],
        "ct": [True, False],
        "ocsp": [True, False],
        "ts": [True, False],
        "srp": [True, False],
        "nextprotoneg": [True, False],
        "comp": [True, False],
        "err": [True, False],
        "stdio": [True, False],
        # 빌드 구성
        "apps": [True, False],
        "docs": [True, False],
        "tests": [True, False],
        "external_tests": [True, False],
        "makedepend": [True, False],
        # 고급 옵션
        "quic": [True, False],
        "dso": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "fPIC": True,
        # 보안 최적화 (기본적으로 보안 중심)
        "enable_fips": False,
        "weak_ssl_ciphers": False,
        # 레거시 프로토콜 비활성화
        "ssl3": False,
        "tls1": False,
        "tls1_1": False,
        "dtls1": False,
        # 압축 지원 (현대적 압축만)
        "zlib": True,
        "brotli": False,
        "zstd": False,
        # 레거시 알고리즘 비활성화
        "rc2": False,
        "rc4": False,
        "rc5": False,
        "md2": False,
        "md4": False,
        "mdc2": False,
        "rmd160": False,
        "idea": False,
        "des": False,
        "bf": False,
        "cast": False,
        "seed": False,
        "gost": False,
        "sm2": False,
        "sm3": False,
        "sm4": False,
        # 불필요한 기능 비활성화
        "cms": False,
        "ct": False,
        "ocsp": False,
        "ts": False,
        "srp": False,
        "nextprotoneg": False,
        "comp": False,
        "err": False,
        "stdio": False,
        # 빌드 최적화
        "apps": False,
        "docs": False,
        "tests": False,
        "external_tests": False,
        "makedepend": False,
        # 고급 기능
        "quic": True,
        "dso": False
    }
    
    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def requirements(self):
        """의존성 설정"""
        if self.options.zlib:
            self.requires(f"zlib/[>=1.2.11]@{self.user}/{self.channel}")
        if self.options.brotli:
            self.requires(f"brotli/[>=1.0.0]@{self.user}/{self.channel}")
        if self.options.zstd:
            self.requires(f"zstd/[>=1.4.0]@{self.user}/{self.channel}")
        
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Android API 레벨 검증
        if self.settings.os == "Android":
            api_level = self.settings.get_safe("os.api_level")
            if api_level and Version(api_level) < "16":
                raise ConanInvalidConfiguration(f"Android API level {api_level} is not supported. Minimum required is 16.")
    
    def validate(self):
        """플랫폼/컴파일러 호환성 검증"""
        # MSVC 버전 검증
        if is_msvc(self) and Version(self.settings.compiler.version) < "190":
            raise ConanInvalidConfiguration(f"MSVC {self.settings.compiler.version} is not supported. Minimum required is 190 (Visual Studio 2015).")
        
        # Apple 플랫폼 검증
        if is_apple_os(self) and self.settings.arch not in ["x86_64", "armv8"]:
            raise ConanInvalidConfiguration(f"Architecture {self.settings.arch} is not supported on {self.settings.os}")
        
        # Android 아키텍처 검증
        if self.settings.os == "Android" and self.settings.arch not in ["armv7", "armv8", "x86", "x86_64"]:
            raise ConanInvalidConfiguration(f"Architecture {self.settings.arch} is not supported on Android")
    
    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        """소스 코드 다운로드 (서브모듈 포함)"""
        git = Git(self)
        git.clone(url="https://github.com/openssl/openssl.git",
                  target=self.source_folder,
                  args=["--branch", f"openssl-{self.version}", "--depth", "1", "--recurse-submodules"])
    
    def _get_openssl_platform(self):
        """OpenSSL Configure 스크립트용 플랫폼 이름 반환"""
        if self.settings.os == "Windows":
            if self.settings.arch == "x86_64":
                return "VC-WIN64A"
            elif self.settings.arch == "armv8":
                return "VC-WIN64-ARM"
            else:
                return "VC-WIN32"
        elif self.settings.os == "Linux":
            if self.settings.arch == "x86_64":
                return "linux-x86_64"
            elif self.settings.arch == "armv8":
                return "linux-aarch64"
            elif self.settings.arch == "armv7":
                return "linux-armv4"
            else:
                return "linux-generic64"
        elif self.settings.os == "Macos":
            if self.settings.arch == "x86_64":
                return "darwin64-x86_64"
            elif self.settings.arch == "armv8":
                return "darwin64-arm64"
        elif self.settings.os == "iOS":
            if self.settings.arch == "armv8":
                return "ios64-cross"
            elif self.settings.arch == "x86_64":
                return "iossimulator-xcrun"
        elif self.settings.os == "Android":
            if self.settings.arch == "armv8":
                return "android-arm64"
            elif self.settings.arch == "armv7":
                return "android-arm"
            elif self.settings.arch == "x86_64":
                return "android-x86_64"
            elif self.settings.arch == "x86":
                return "android-x86"
        
        return "linux-generic64"  # 기본값
    
    def _get_configure_options(self):
        """Configure 스크립트 옵션 생성"""
        options = []
        
        # 기본 설정
        if self.options.shared:
            options.append("shared")
        else:
            options.append("no-shared")
            options.append("no-dso")
        
        # 보안 기능
        if not self.options.enable_fips:
            options.extend(["no-fips", "no-fips-securitychecks"])
        
        if not self.options.weak_ssl_ciphers:
            options.append("no-weak-ssl-ciphers")
        
        # 프로토콜 지원
        if not self.options.ssl3:
            options.extend(["no-ssl3", "no-ssl3-method"])
        if not self.options.tls1:
            options.append("no-tls1")
        if not self.options.tls1_1:
            options.append("no-tls1_1")
        if not self.options.dtls1:
            options.append("no-dtls1")
        
        # 압축 지원
        if self.options.zlib:
            options.append("enable-zlib")
        if self.options.brotli:
            options.append("enable-brotli")
        if self.options.zstd:
            options.append("enable-zstd")
        
        # 고급 기능
        if self.options.quic:
            options.append("enable-quic")
        
        # 알고리즘 비활성화
        disabled_algos = []
        if not self.options.rc2: disabled_algos.append("rc2")
        if not self.options.rc4: disabled_algos.append("rc4")
        if not self.options.rc5: disabled_algos.append("rc5")
        if not self.options.md2: disabled_algos.append("md2")
        if not self.options.md4: disabled_algos.append("md4")
        if not self.options.mdc2: disabled_algos.append("mdc2")
        if not self.options.rmd160: disabled_algos.append("rmd160")
        if not self.options.idea: disabled_algos.append("idea")
        if not self.options.des: disabled_algos.append("des")
        if not self.options.bf: disabled_algos.append("bf")
        if not self.options.cast: disabled_algos.append("cast")
        if not self.options.seed: disabled_algos.append("seed")
        if not self.options.gost: disabled_algos.append("gost")
        if not self.options.sm2: disabled_algos.append("sm2")
        if not self.options.sm3: disabled_algos.append("sm3")
        if not self.options.sm4: disabled_algos.append("sm4")
        
        for algo in disabled_algos:
            options.append(f"no-{algo}")
        
        # 기능 모듈 비활성화
        disabled_features = []
        if not self.options.cms: disabled_features.append("cms")
        if not self.options.ct: disabled_features.append("ct")
        if not self.options.ocsp: disabled_features.append("ocsp")
        if not self.options.ts: disabled_features.append("ts")
        if not self.options.srp: disabled_features.append("srp")
        if not self.options.nextprotoneg: disabled_features.append("nextprotoneg")
        if not self.options.comp: disabled_features.append("comp")
        if not self.options.err: disabled_features.append("err")
        if not self.options.stdio: disabled_features.append("stdio")
        
        for feature in disabled_features:
            options.append(f"no-{feature}")
        
        # 빌드 구성
        if not self.options.apps: options.append("no-apps")
        if not self.options.docs: options.append("no-docs")
        if not self.options.tests: 
            options.extend(["no-tests", "no-external-tests", "no-fuzz-libfuzzer", "no-fuzz-afl"])
        if not self.options.makedepend: options.append("no-makedepend")
        
        return options
    
    def generate(self):
        """환경변수 설정"""
        if not is_msvc(self):
            # Unix 계열에서 AutotoolsToolchain 사용
            tc = AutotoolsToolchain(self)
            tc.generate()
        
        # Android 전용 환경변수 설정
        if self.settings.os == "Android":
            env = Environment()
            android_ndk = self.conf.get("tools.android:ndk_path")
            if android_ndk:
                env.define("ANDROID_NDK_ROOT", android_ndk)
                env.define("ANDROID_API", self.settings.get_safe("os.api_level", "24"))
            #env.apply()
    
    def build(self):
        """패키지 빌드"""
        # OpenSSL Configure 스크립트 실행
        openssl_platform = self._get_openssl_platform()
        options = self._get_configure_options()
        
        # 설치 경로를 프로젝트 내 build 디렉토리로 설정
        build_dir = os.path.join(os.getcwd(), "build", "local").replace("\\", "/")
        os.makedirs(build_dir, exist_ok=True)
        
        # OpenSSL 설정 디렉토리도 프로젝트 내로 설정
        openssldir = os.path.join(build_dir, "ssl").replace("\\", "/")
        
        # Configure 명령어 구성
        configure_cmd = ["perl", "./Configure", openssl_platform, f"--prefix={build_dir}", f"--openssldir={openssldir}"]
        
        # Android의 경우 API 레벨 매크로만 추가 (컴파일러 경로는 PATH에서 자동 탐지)
        if self.settings.os == "Android":
            api_level = os.environ.get('ANDROID_API', '21')
            configure_cmd.append(f"-D__ANDROID_API__={api_level}")
            
        configure_cmd.extend(options)
        
        self.output.info(f"Configuring OpenSSL with: {' '.join(configure_cmd)}")
        
        with chdir(self, self.source_folder):
            # Android의 경우: NDK clang을 PATH에서 자동 인식시키도록 PATH만 선두에 추가
            if self.settings.os == "Android":
                android_ndk = os.environ.get('ANDROID_NDK_ROOT')
                if android_ndk:
                    # NDK 툴체인 bin을 PATH 가장 앞에 추가
                    if platform.system() == "Windows":
                        ndk_host = "windows-x86_64"
                    elif platform.system() == "Darwin":
                        ndk_host = "darwin-x86_64"
                    else:
                        ndk_host = "linux-x86_64"
                    # Use forward slashes so Configure's regex (with /prebuilt/) can match
                    ndk_bin = f"{android_ndk}/toolchains/llvm/prebuilt/{ndk_host}/bin"
                    current_path = os.environ.get('PATH', '')
                    if platform.system() == "Windows":
                        os.environ['PATH'] = f"{ndk_bin};{current_path}"
                    else:
                        os.environ['PATH'] = f"{ndk_bin}:{current_path}"
                    # GCC 프리픽스 자동 탐지에 걸리지 않도록 CROSS_COMPILE 제거
                    if 'CROSS_COMPILE' in os.environ:
                        del os.environ['CROSS_COMPILE']
                    # Windows 호스트일 때는 OpenSSL이 triple-gcc를 찾는 경로로 빠지지 않도록
                    # clang 툴들을 직접 지정하고 --target/--sysroot를 전달한다.
                    if platform.system() == "Windows":
                        toolchain_root = f"{android_ndk}/toolchains/llvm/prebuilt/{ndk_host}"
                        sysroot = f"{toolchain_root}/sysroot"

                        # 아키텍처별 타겟 트리플
                        if str(self.settings.arch) == "armv8":
                            triple = "aarch64-linux-android"
                        elif str(self.settings.arch) == "armv7":
                            triple = "armv7a-linux-androideabi"
                        elif str(self.settings.arch) == "x86_64":
                            triple = "x86_64-linux-android"
                        elif str(self.settings.arch) == "x86":
                            triple = "i686-linux-android"
                        else:
                            triple = None

                        if triple:
                            api = os.environ.get('ANDROID_API', '24')
                            target_flag = f"--target={triple}{api}"
                            sysroot_flag = f"--sysroot={sysroot}"

                            # 환경변수로 최소 지정
                            os.environ['CC'] = 'clang'
                            os.environ['CXX'] = 'clang++'
                            os.environ['AR'] = 'llvm-ar'
                            os.environ['RANLIB'] = 'llvm-ranlib'
                            os.environ['STRIP'] = 'llvm-strip'

                            # 기존 플래그에 추가
                            extra_cflags = f"{target_flag} {sysroot_flag}"
                            os.environ['CFLAGS'] = (os.environ.get('CFLAGS', '') + ' ' + extra_cflags).strip()
                            os.environ['CXXFLAGS'] = (os.environ.get('CXXFLAGS', '') + ' ' + extra_cflags).strip()

                            # 확인용 출력
                            self.output.info(f"Using clang with: {target_flag} {sysroot_flag}")
                            self.output.info(f"CC={os.environ['CC']} CXX={os.environ['CXX']}")
                
                self.output.info("Android 환경변수:")
                self.output.info(f"  ABI={os.environ.get('ABI', 'NOT_SET')}")
                self.output.info(f"  CC={os.environ.get('CC', 'NOT_SET')}")
                self.output.info(f"  CXX={os.environ.get('CXX', 'NOT_SET')}")
                self.output.info(f"  SYSROOT={os.environ.get('SYSROOT', 'NOT_SET')}")
                self.output.info(f"  ANDROID_API={os.environ.get('ANDROID_API', 'NOT_SET')}")
                self.output.info(f"  ANDROID_NDK_ROOT={os.environ.get('ANDROID_NDK_ROOT', 'NOT_SET')}")
                self.output.info(f"  CROSS_COMPILE={os.environ.get('CROSS_COMPILE', 'NOT_SET')}")
            
            # Configure 실행
            self.run(" ".join(configure_cmd))
            
            # 빌드 실행
            if self.settings.os == "Windows":
                self.run("nmake")
            else:
                # CPU 코어 수에 따른 병렬 빌드
                import multiprocessing
                jobs = multiprocessing.cpu_count()
                self.run(f"make -j{jobs}")

            self.output.info(f"  Package folder: {self.package_folder}")
    
    def package(self):
        """패키지 파일 복사"""
        # 먼저 임시 build 디렉토리에 설치
        build_dir = os.path.join(os.getcwd(), "build", "local").replace("\\", "/")
        
        with chdir(self, self.source_folder):
            if self.settings.os == "Windows":
                #self.run(f"nmake install DESTDIR=\"\" INSTALLTOP=\"{build_dir}\" OPENSSLDIR=\"{build_dir}/ssl\"")
                self.run(f"nmake install")
            else:
                #self.run(f"make install DESTDIR='' INSTALLTOP=\"{build_dir}\" OPENSSLDIR=\"{build_dir}/ssl\"")
                self.run(f"make install")
        
        # 빌드된 파일들을 패키지 폴더로 복사
        self.output.info(f"  Package folder: {self.package_folder}")
        copy(self, "*.h", src=os.path.join(build_dir, "include"), dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.lib", src=os.path.join(build_dir, "lib"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=os.path.join(build_dir, "lib"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=os.path.join(build_dir, "lib64"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", src=os.path.join(build_dir, "lib"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", src=os.path.join(build_dir, "lib64"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib*", src=os.path.join(build_dir, "lib"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dll", src=os.path.join(build_dir, "bin"), dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.exe", src=os.path.join(build_dir, "bin"), dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # 라이선스 파일 복사
        copy(self, "LICENSE*", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        
        # CMake 모듈 변수 파일 생성
        self._create_cmake_module_variables(os.path.join(self.package_folder, self._module_vars_file))
        
        # Apple 공유 라이브러리 이름 수정 (필요시)
        if is_apple_os(self) and self.options.shared:
            fix_apple_shared_install_name(self)
    
    @property
    def _module_vars_file(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}.cmake")
    
    def _create_cmake_module_variables(self, module_file):
        """CMake 모듈 변수 파일 생성"""
        content = textwrap.dedent(f"""
            # OpenSSL CMake 변수 설정
            set(OPENSSL_FOUND TRUE)
            set(OPENSSL_INCLUDE_DIR "${{CONAN_INCLUDE_DIRS_OPENSSL}}")
            set(OPENSSL_CRYPTO_LIBRARY "${{CONAN_LIBS_OPENSSL_CRYPTO}}")
            set(OPENSSL_SSL_LIBRARY "${{CONAN_LIBS_OPENSSL_SSL}}")
            set(OPENSSL_LIBRARIES "${{CONAN_LIBS_OPENSSL}}")
            set(OPENSSL_VERSION "{self.version}")
            
            # OpenSSL 1.1+ 호환성을 위한 변수
            set(OPENSSL_CRYPTO_LIBRARIES "${{OPENSSL_CRYPTO_LIBRARY}}")
            set(OPENSSL_SSL_LIBRARIES "${{OPENSSL_SSL_LIBRARY}}")
            
            # 레거시 변수 지원
            set(OPENSSL_ROOT_DIR "${{CONAN_OPENSSL_ROOT}}")
            """)
        save(self, module_file, content)
    
    def compatibility(self):
        """
        패키지 바이너리 호환성 설정
        
        이 메서드는 Conan이 패키지를 찾을 때 "호환 가능한" 설정 조합을 정의합니다.
        예: cppstd=20으로 빌드된 패키지를 cppstd=14 환경에서도 사용 가능하게 함.
        
        순수 C 라이브러리(OpenSSL 등)는 C++ 표준이나 컴파일러 버전에 영향받지 않으므로,
        이러한 설정이 달라도 동일한 바이너리를 재사용할 수 있습니다.
        
        이를 통해:
        - 불필요한 재빌드 방지
        - 다양한 프로젝트 설정에서 동일 패키지 공유 가능
        - compiler.cppstd=14/17/20/23 모두에서 같은 패키지 사용
        - compiler.version=193/194 등 버전 차이에서도 호환
        """
        return [
            # C++ 표준이 달라도 호환 (순수 C 라이브러리이므로 영향 없음)
            {"settings": [("compiler.cppstd", None)]},
            # 컴파일러 버전이 달라도 호환 (같은 컴파일러 내에서 ABI 호환)
            {"settings": [("compiler.version", None)]},
            # runtime_type이 달라도 호환
            {"settings": [("compiler.runtime_type", None)]},
            # 위 설정들의 조합도 호환
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
        # 라이브러리 경로 설정
        #self.cpp_info.libdirs = ["lib"]
        #self.cpp_info.includedirs = ["include"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "openssl")
        
        # CMake 설정 - 표준 OpenSSL CMake 타겟과 호환되도록 설정
        self.cpp_info.set_property("cmake_file_name", "OpenSSL")
        
        # 라이브러리 이름 설정 (플랫폼별 일관성 유지)
        if self.settings.os == "Windows":
            # Windows에서는 .lib 확장자 없이 라이브러리 이름 사용
            ssl_lib = "libssl"
            crypto_lib = "libcrypto"
        else:
            ssl_lib = "ssl"
            crypto_lib = "crypto"
        
        # components 설정 - 표준 OpenSSL CMake 타겟과 호환
        self.cpp_info.components["ssl"].libs = [ssl_lib]
        self.cpp_info.components["ssl"].set_property("cmake_target_name", "OpenSSL::SSL")
        self.cpp_info.components["ssl"].set_property("pkg_config_name", "libssl")
        
        self.cpp_info.components["crypto"].libs = [crypto_lib]
        self.cpp_info.components["crypto"].set_property("cmake_target_name", "OpenSSL::Crypto")
        self.cpp_info.components["crypto"].set_property("pkg_config_name", "libcrypto")
        
        # 시스템 라이브러리 설정
        if self.settings.os == "Windows":
            if not self.options.shared:
                # Windows 정적 링크 시 필요한 시스템 라이브러리들 (완전한 목록)
                win_libs = ["ws2_32", "gdi32", "advapi32", "crypt32", "user32", "winmm", "bcrypt"]
                self.cpp_info.components["ssl"].system_libs = win_libs
                self.cpp_info.components["crypto"].system_libs = win_libs
        else:
            # Unix 계열에서 필요한 시스템 라이브러리들
            if self.settings.os == "Linux":
                linux_libs = ["dl", "pthread"]
                if not self.options.shared:
                    linux_libs.append("rt")  # 정적 링크 시 추가
                self.cpp_info.components["ssl"].system_libs = linux_libs
                self.cpp_info.components["crypto"].system_libs = linux_libs
            elif self.settings.os in ["Macos", "iOS"]:
                # Apple 프레임워크 설정
                apple_frameworks = ["Security", "CoreFoundation"]
                self.cpp_info.components["ssl"].frameworks = apple_frameworks
                self.cpp_info.components["crypto"].frameworks = apple_frameworks
            elif self.settings.os == "Android":
                # Android 시스템 라이브러리
                android_libs = ["dl", "log"]
                self.cpp_info.components["ssl"].system_libs = android_libs
                self.cpp_info.components["crypto"].system_libs = android_libs
        
        # 의존성 라이브러리 연결
        if self.options.zlib:
            self.cpp_info.components["ssl"].requires.append("zlib::zlib")
            self.cpp_info.components["crypto"].requires.append("zlib::zlib")
        if self.options.brotli:
            self.cpp_info.components["ssl"].requires.append("brotli::brotli")
            self.cpp_info.components["crypto"].requires.append("brotli::brotli")
        if self.options.zstd:
            self.cpp_info.components["ssl"].requires.append("zstd::zstd")
            self.cpp_info.components["crypto"].requires.append("zstd::zstd")
        
        # SSL 컴포넌트는 crypto에 의존
        self.cpp_info.components["ssl"].requires.append("crypto")
        
        # 디버깅 정보 출력
        self.output.info(f"OpenSSL {self.version} configured with:")
        self.output.info(f"  Platform: {self._get_openssl_platform()}")
        self.output.info(f"  Options: {' '.join(self._get_configure_options())}")
        self.output.info(f"  SSL Library: {ssl_lib}")
        self.output.info(f"  Crypto Library: {crypto_lib}")
        self.output.info(f"  Libdirs: {self.cpp_info.libdirs}")
        self.output.info(f"  Includedirs: {self.cpp_info.includedirs}")
        
        # 패키지 폴더 경로 출력 (이것이 openssl_PACKAGE_FOLDER_RELEASE가 됨)
        self.output.info(f"  PACKAGE_FOLDER (will be openssl_PACKAGE_FOLDER_RELEASE): {self.package_folder}")
        
        # 패키지 폴더 내용 확인
        import os
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.exists(lib_dir):
            self.output.info(f"  Package lib directory contents:")
            for file in os.listdir(lib_dir):
                self.output.info(f"    {file}")
        else:
            self.output.info(f"  Package lib directory does not exist: {lib_dir} , {self.cpp.package.libs}")
