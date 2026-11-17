import json
from conan import ConanFile
from conan.tools.files import copy
import os


class FMODConan(ConanFile):
    name = "fmod"
    version = "2.02.30"
    user = "sc"
    channel = "prebuilt"
    
    description = "FMOD Studio is a professional audio engine"
    homepage = "https://www.fmod.com/"
    license = "FMOD-License"
    
    settings = "os", "arch", "compiler", "build_type"
    
    # Export all source files with directory structure
    exports_sources = "android/*", "ios/*", "windows/*"

    def package(self):
        # Determine platform and architecture
        platform_arch = self._get_platform_arch()
        if not platform_arch:
            self.output.error(f"Unsupported platform/arch combination: {self.settings.os}/{self.settings.arch}")
            return
            
        platform, arch = platform_arch
        source_dir = os.path.join(self.source_folder, platform, arch)
        
        # Copy headers
        copy(self, "*.h", 
             src=os.path.join(source_dir, "include"), 
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "*.hpp", 
             src=os.path.join(source_dir, "include"), 
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        
        # Copy libraries
        copy(self, "*.a", 
             src=os.path.join(source_dir, "lib"), 
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.so", 
             src=os.path.join(source_dir, "lib"), 
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.lib", 
             src=os.path.join(source_dir, "lib"), 
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        
        # Copy binaries (Windows DLLs)
        if platform == "windows":
            copy(self, "*.dll", 
                 src=os.path.join(source_dir, "bin"), 
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
        
        # Copy Android JAR file
        if platform == "android":
            jar_file = os.path.join(self.source_folder, platform, "fmod.jar")
            if os.path.exists(jar_file):
                copy(self, "fmod.jar", 
                     src=os.path.join(self.source_folder, platform), 
                     dst=os.path.join(self.package_folder, "lib"),
                     keep_path=False)
                                
    def package_id(self):
        try:
            del self.info.settings.build_type
        except:
            pass
        try:
            del self.info.settings.compiler.runtime_type
        except:
            pass
        
        settings_info = {
            "os": str(self.info.settings.os),
            "arch": str(self.info.settings.arch),
            "compiler": str(self.info.settings.compiler)
        }
        self.output.info("package_id keys: " + json.dumps(settings_info, indent=2))

    def package_info(self):
        # Set include directories
        self.cpp_info.includedirs = ["include"]
        
        # Set library directories
        self.cpp_info.libdirs = ["lib"]
        
        # Set binary directories for Windows
        if self.settings.os == "Windows":
            self.cpp_info.bindirs = ["bin"]
        
        # CMake support
        self.cpp_info.set_property("cmake_target_name", "fmod::fmod")
        
        # FMOD Core component
        if self.settings.os == "iOS":
            fmod_lib = "fmod_iphoneos"
            fmodstudio_lib = "fmodstudio_iphoneos"
        elif self.settings.os == "Windows":
            if self.settings.build_type == "Debug":
                fmod_lib = "fmodL_vc"
                fmodstudio_lib = "fmodstudioL_vc"
            else:
                fmod_lib = "fmod_vc"
                fmodstudio_lib = "fmodstudio_vc"
        else:
            fmod_lib = "fmod"
            fmodstudio_lib = "fmodstudio"
        
        # # FMOD Core
        self.cpp_info.components["core"].includedirs = [os.path.join(self.package_folder, "include")]
        self.cpp_info.components["core"].libs = [fmod_lib]
        self.cpp_info.components["core"].set_property("cmake_target_name", "FMOD::core")
        
        # # FMOD Studio
        self.cpp_info.components["studio"].libs = [fmodstudio_lib]
        self.cpp_info.components["studio"].requires = ["core"]
        self.cpp_info.components["studio"].set_property("cmake_target_name", "FMOD::studio")
        
        # Set main libs for backward compatibility
        self.cpp_info.libs = [fmod_lib, fmodstudio_lib]
        
        # Platform-specific settings
        if self.settings.os == "Android":
            self.cpp_info.system_libs = ["log"]
            # Add JAR file info for Android
            jar_path = os.path.join(self.package_folder, "lib", "fmod.jar")
            if os.path.exists(jar_path):
                self.cpp_info.set_property("java_libs", ["fmod.jar"])
                
        elif self.settings.os == "iOS":
            self.cpp_info.frameworks = ["AudioToolbox", "CoreAudio"]
            self.cpp_info.components["core"].frameworks = ["AudioToolbox", "CoreAudio"]
            
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["winmm", "ole32", "user32"]
            self.cpp_info.components["core"].system_libs = ["winmm", "ole32", "user32"]
        
        self.output.info(f"FMOD {self.version} configured with:")
        self.output.info(f"  Includes: {self.cpp_info.includedirs}")
        self.output.info(f"  Libs: {self.cpp_info.libs}")
    
    def _get_platform_arch(self):
        """Map Conan settings to directory structure"""
        os_map = {
            "Android": "android",
            "iOS": "ios", 
            "Windows": "windows"
        }
        
        arch_map = {
            "armv8": "arm64-v8a",      # Android ARM64
            "armv7": "armeabi-v7a",    # Android ARM32
            "x86": "x86",              # Android x86
            "x86_64": "x86_64",        # Android x86_64
            "armv8-32": "arm64",       # iOS ARM64
            "x86_64": "x64"            # Windows x64
        }
        
        platform = os_map.get(str(self.settings.os))
        if not platform:
            return None
            
        # Special handling for different platforms
        if self.settings.os == "iOS" and self.settings.arch in ["armv8", "armv8-32"]:
            arch = "arm64"
        elif self.settings.os == "Windows" and self.settings.arch == "x86_64":
            arch = "x64"
        else:
            arch = arch_map.get(str(self.settings.arch))
            
        if not arch:
            return None
            
        return platform, arch