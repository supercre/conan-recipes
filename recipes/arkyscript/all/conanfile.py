import os

from conan import ConanFile
from conan.tools.files import copy, get, save


class ArkyscriptConan(ConanFile):
    name = "arkyscript"
    package_type = "header-library"
    description = "Arky C++20 host bindings for an existing LuaJIT VM"
    url = "https://github.com/supercre/conan-recipes"
    homepage = "https://github.com/supercre/arkyscript"
    topics = ("lua", "luajit", "bindings", "arky")
    no_copy_source = True

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], filename="source.tar.gz", strip_root=True)

    def package(self):
        # 호스트의 LuaJIT를 사용하므로 다른 Lua 런타임을 의존성으로 추가하지 않는다.
        for pattern in ("*.h", "*.inl"):
            copy(self, pattern, os.path.join(self.source_folder, "binder"),
                 os.path.join(self.package_folder, "include", "binder"))
        copy(self, "README.md", os.path.join(self.source_folder, "binder"),
             os.path.join(self.package_folder, "res", "binder"))
        copy(self, "dependencies.json", self.source_folder,
             os.path.join(self.package_folder, "res"))
        save(self, os.path.join(self.package_folder, "res", "arkyscript.cmake"),
             "if(TARGET arkyscript::binder)\n"
             "  target_compile_features(arkyscript::binder INTERFACE cxx_std_20)\n"
             "endif()\n")

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "arkyscript")
        self.cpp_info.set_property("cmake_target_name", "arkyscript::binder")
        self.cpp_info.set_property("cmake_build_modules", ["res/arkyscript.cmake"])
