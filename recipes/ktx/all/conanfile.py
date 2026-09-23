import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git


class KtxConan(ConanFile):
    name = "ktx"
    version = "4.4.2"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "Khronos KTX texture library (libktx)"
    homepage = "https://github.com/KhronosGroup/KTX-Software"
    license = "Apache-2.0"
    topics = ("ktx", "texture", "graphics")

    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": False,     # 정적 라이브러리 기본값
        "fPIC": True,
        "with_tools": False  # 도구 비활성화 기본값
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
        git = Git(self)
        git.clone(
            url="https://github.com/KhronosGroup/KTX-Software.git",
            target=self.source_folder,
            args=[
                # "--branch", f"v{self.version}", # C++20 빌드 이슈가 있어서 임시로 일단 main 브랜치 받도록 함.
                "--branch", "main",
                "--depth", "1",
                "--recurse-submodules"
            ],
        )

    def generate(self):
        """빌드 파일 생성"""
        tc = CMakeToolchain(self)
        if self.settings.os == "Windows" and self.settings.compiler == "msvc":
            tc.generator = "Visual Studio 18 2026"
            tc.toolset = "v194"
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared

        # libktx만 빌드: 도구/테스트/문서 비활성화
        tc.cache_variables["KTX_FEATURE_TOOLS"] = self.options.with_tools
        tc.cache_variables["KTX_FEATURE_TESTS"] = False
        tc.cache_variables["KTX_FEATURE_TOOLS_CTS"] = False
        tc.cache_variables["KTX_FEATURE_LOADTEST_APPS"] = False
        tc.cache_variables["KTX_FEATURE_DOC"] = False
        tc.cache_variables["KTX_FEATURE_JNI"] = False
        tc.cache_variables["KTX_FEATURE_PY"] = False
        tc.cache_variables["KTX_FEATURE_VK_UPLOAD"] = False
        # tc.cache_variables["KTX_GIT_VERSION_FULL"] = f"v{self.version}"

        # msvc debug 빌드에서 iterator debug assert 때문에 진행이 안되는 이슈가 있어서 끔.
        if self.settings.compiler == "msvc" and self.settings.build_type == "Debug":
            tc.preprocessor_definitions["_ITERATOR_DEBUG_LEVEL"] = 0
        

        # 정적 라이브러리 옵션(미지원 버전에서도 무해)
        tc.cache_variables["KTX_FEATURE_STATIC_LIBRARY"] = not self.options.shared

        tc.generate()

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
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def compatibility(self):
        """
        패키지 바이너리 호환성 설정
        """
        return [
            {"settings": [("compiler.cppstd", None)]},
            {"settings": [("compiler.version", None)]},
            {"settings": [("compiler.runtime_type", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None), ("compiler.runtime_type", None)]},
        ]

    def package_id(self):
        # del self.info.settings.build_type
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
        """패키지 정보 설정"""
        self.cpp_info.libs = ["ktx"]

