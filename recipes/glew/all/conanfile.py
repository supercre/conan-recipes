import json
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.scm import Git
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.errors import ConanException
import os


class GlewConan(ConanFile):
    name = "glew"
    version = "2.2.0"
    user = "sc"
    channel = "dev"
    # Metadata
    description = "The OpenGL Extension Wrangler Library"
    homepage = "https://github.com/nigels-com/glew"
    license = "Modified BSD License"
    topics = ("opengl", "graphics", "extension", "wrangler")
    
    # Package configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_utils": [True, False],
        "glew_regal": [True, False],
        "glew_osmesa": [True, False],
        "glew_x11": [True, False],
        "glew_egl": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_utils": False,
        "glew_regal": False,
        "glew_osmesa": False,
        "glew_x11": True,
        "glew_egl": False
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
        cmake_layout(self)
        self.folders.source = "src"
   
    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def source(self):
        git = Git(self)
        git.clone(url="https://github.com/nigels-com/glew.git",
                  target=self.source_folder,
                  args=["--branch", f"glew-{self.version}", "--depth", "1"])
    
    def build(self):
        # Wrapper CMakeLists.txt 생성
        wrapper_cmake = os.path.join(self.build_folder, "CMakeLists.txt")
        with open(wrapper_cmake, 'w') as f:
            f.write(f"""cmake_minimum_required(VERSION 3.16)
set(CMAKE_POLICY_DEFAULT_CMP0091 NEW)

# GLEW 옵션 설정
set(BUILD_UTILS {str(self.options.build_utils).upper()})
set(GLEW_REGAL {str(self.options.glew_regal).upper()})
set(GLEW_OSMESA {str(self.options.glew_osmesa).upper()})
set(GLEW_X11 {str(self.options.glew_x11).upper()})
set(GLEW_EGL {str(self.options.glew_egl).upper()})
set(BUILD_SHARED_LIBS {str(self.options.shared).upper()})

# 원본 CMakeLists.txt 포함
add_subdirectory({os.path.join(self.source_folder, "build", "cmake").replace(os.sep, '/')} glew)
""")
        
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    
    def package(self):
        cmake = CMake(self)
        cmake.install()
        
        # 라이선스 파일 복사
        copy(self, "LICENSE.txt", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
    
    
    def package_id(self):
        del self.info.settings.build_type
        del self.info.settings.compiler.runtime_type
        settings_info = {
            "os": str(self.info.settings.os),
            "arch": str(self.info.settings.arch),
            "compiler": str(self.info.settings.compiler)
        }
        self.output.info(f"{json.dumps(settings_info,indent=4)}")

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["GLEW"]
        else:
            self.cpp_info.libs = ["GLEW_s" if self.settings.os == "Windows" else "GLEW"]
            self.cpp_info.defines = ["GLEW_STATIC"]
        
        # 플랫폼별 시스템 라이브러리 및 프레임워크
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["opengl32"]
        elif self.settings.os == "Linux":
            self.cpp_info.system_libs = ["GL"]
            if self.options.glew_x11:
                self.cpp_info.system_libs.extend(["X11", "Xext", "Xi", "Xmu"])
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["OpenGL", "Cocoa"]
        elif self.settings.os == "Android":
            self.cpp_info.system_libs = ["GLESv2", "EGL"]
        elif self.settings.os == "iOS":
            self.cpp_info.frameworks = ["OpenGLES"]
        
        # pkg-config 설정
        self.cpp_info.set_property("pkg_config_name", "glew")
        
        # CMake 타겟 설정
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "glew")
        if self.options.shared:
            self.cpp_info.set_property("cmake_target_name", "GLEW::glew")
        else:
            self.cpp_info.set_property("cmake_target_name", "GLEW::glew_s")
