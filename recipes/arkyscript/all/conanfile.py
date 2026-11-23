import os

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.scm import Version


class ArkyscriptConan(ConanFile):
    name = "arkyscript"
    package_type = "header-library"
    description = "Arky C++20 host bindings and host runtime for an existing LuaJIT VM"
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
        module = ("if(TARGET arkyscript::binder)\n"
                  "  target_compile_features(arkyscript::binder INTERFACE cxx_std_20)\n"
                  "endif()\n")
        if Version(self.version) >= "0.5.0":
            # 호스트 런타임(스케줄러·Task·I/O·정적 import)은 소스로 넣는다. 호스트는
            # include/runtime/arky_runtime.cpp 한 파일을 자기 LuaJIT와 함께 컴파일한다.
            runtime = os.path.join(self.source_folder, "runtime")
            target = os.path.join(self.package_folder, "include", "runtime")
            for pattern in ("arky_runtime.h", "arky_runtime.cpp", "arky_runtime_lua.inc",
                            "task/task_pool.h", "task/lua_task.cpp", "io/lua_io.cpp"):
                copy(self, pattern, runtime, target)
            copy(self, "embedding.md", os.path.join(self.source_folder, "docs"),
                 os.path.join(self.package_folder, "res", "runtime"))
            module += ('get_filename_component(ARKYSCRIPT_RUNTIME_SOURCE\n'
                       '  "${CMAKE_CURRENT_LIST_DIR}/../include/runtime/arky_runtime.cpp" ABSOLUTE)\n')
        save(self, os.path.join(self.package_folder, "res", "arkyscript.cmake"), module)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "arkyscript")
        self.cpp_info.set_property("cmake_target_name", "arkyscript::binder")
        self.cpp_info.set_property("cmake_build_modules", ["res/arkyscript.cmake"])
