import json
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import get, copy
from conan.tools.scm import Git
from conan.errors import ConanException
import os


class Glfw3Conan(ConanFile):
    name = "glfw3"
    version = "3.4"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "Multi-platform library for OpenGL, OpenGL ES, Vulkan, window and input"
    homepage = "https://github.com/glfw/glfw"
    license = "Zlib"
    topics = ("opengl", "vulkan", "window", "input", "graphics")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vulkan_static": [True, False]
    }
    default_options = {
        "shared": False,  # 정적 라이브러리 기본값
        "fPIC": True,
        "vulkan_static": False
    }
    
    def config_options(self):
        """플랫폼별 옵션 제거"""
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os in ["Android", "iOS"]:
            del self.options.vulkan_static  # 모바일에서는 Vulkan 정적 링크 불필요
    
    def configure(self):
        """설정 조정"""
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def layout(self):
        """디렉토리 레이아웃 설정"""
        cmake_layout(self)
        self.folders.source = "src"
   
    def source(self):
        """소스 코드 다운로드"""
        # Git을 사용하여 GLFW 소스 다운로드
        git = Git(self)
        git.clone(url="https://github.com/glfw/glfw.git",
                  target=self.source_folder,
                  args=["--branch", f"{self.version}", "--depth", "1"])
    
    def generate(self):
        """빌드 파일 생성"""
        # CMake 툴체인 및 종속성 생성
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["GLFW_BUILD_EXAMPLES"] = False
        tc.variables["GLFW_BUILD_TESTS"] = False
        tc.variables["GLFW_BUILD_DOCS"] = False
        tc.variables["GLFW_INSTALL"] = True
        tc.variables["GLFW_LIBRARY_TYPE"] = "STATIC"
        
        if self.options.get_safe("vulkan_static"):
            tc.variables["GLFW_VULKAN_STATIC"] = True
        
        # Android 특별 설정 - GLFW는 Android를 직접 지원하지 않음
        if self.settings.os == "Android":
            # Android에서는 일반적으로 GLFW 대신 Android NDK의 네이티브 윈도우 API 사용
            self.output.warn("GLFW does not officially support Android. Consider using Android NDK native window APIs.")
        
        # iOS 특별 설정 - GLFW는 iOS를 직접 지원하지 않음
        elif self.settings.os == "iOS":
            # iOS에서는 일반적으로 GLFW 대신 Metal 또는 GLKit 사용
            self.output.warn("GLFW does not officially support iOS. Consider using Metal or GLKit.")
        
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
                        
        #copy(self, "*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        #copy(self, "*", src=os.path.join(self.build_folder, "src", self.settings.build_type), dst=os.path.join(self.package_folder, "lib"))        

        #self.output.info(f"package_folder: {self.package_folder}")
        #self.output.info(f"build_folder: {self.build_folder}")
        #self.output.info(f"source_folder: {self.source_folder}")
        #self.output.info(f"include_folder: {os.path.join(self.source_folder, 'include')}")
        #self.output.info(f"lib_folder: {os.path.join(self.build_folder, 'src', self.settings.build_type)}")
       #self.output.info(f"package include_folder: {os.path.join(self.package_folder, 'include')}")
       # self.output.info(f"package lib_folder: {os.path.join(self.package_folder, 'lib')}")



        # 라이선스 파일 복사
        copy(self, "LICENSE.md", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
    
    def compatibility(self):
        """
        패키지 바이너리 호환성 설정

        순수 C 라이브러리는 C++ 표준(cppstd)이나 컴파일러 버전에 영향받지 않으므로,
        이러한 설정이 달라도 동일한 바이너리를 재사용할 수 있습니다.
        예: cppstd=20으로 빌드된 패키지를 cppstd=14 환경에서도 사용 가능.
        """
        result = [
            {"settings": [("compiler.cppstd", None)]},
            {"settings": [("compiler.version", None)]},
            {"settings": [("compiler.cppstd", None), ("compiler.version", None)]},
        ]
        # compiler.runtime_type은 MSVC 전용 설정
        if str(self.settings.compiler) == "msvc":
            result.extend([
                {"settings": [("compiler.runtime_type", None)]},
                {"settings": [("compiler.cppstd", None), ("compiler.version", None), ("compiler.runtime_type", None)]},
            ])
        return result

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
        self.cpp_info.libs = ["glfw3"]
        
        # 플랫폼별 시스템 라이브러리 및 프레임워크
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["gdi32", "user32", "shell32"]
        elif self.settings.os == "Linux":
            self.cpp_info.system_libs = ["m", "X11", "Xrandr", "Xinerama", "Xcursor", "Xxf86vm", "Xi", "dl", "pthread"]
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["Cocoa", "IOKit", "CoreFoundation"]
            if self.options.get_safe("vulkan_static", False):
                self.cpp_info.frameworks.append("QuartzCore")
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "glfw3")
        
        # CMake 타겟 설정
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "glfw")
        self.cpp_info.set_property("cmake_target_name", "glfw")

