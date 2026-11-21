import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


class LuaCjsonConan(ConanFile):
    name = "lua-cjson"
    package_type = "static-library"
    license = "MIT"
    description = "Lua CJSON with exact LuaJIT int64_t and uint64_t support"
    url = "https://github.com/supercre/conan-recipes"
    homepage = "https://github.com/supercre/lua-cjson"
    topics = ("lua", "luajit", "json", "int64")
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            filename="cjson.tar.gz", destination="cjson", strip_root=True)
        # 공개 Lua 5.1 ABI 헤더만 사용한다. LuaJIT 런타임은 소비자가 제공한다.
        get(self, **self.conan_data["luajit_headers"],
            filename="luajit.tar.gz", destination="luajit", strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CJSON_BUILD_STATIC"] = True
        toolchain.variables["LUA_INCLUDE_DIR"] = os.path.join(self.source_folder, "luajit", "src")
        if self.settings.os == "Macos":
            toolchain.cache_variables["CMAKE_OSX_DEPLOYMENT_TARGET"] = str(
                self.settings.os.get_safe("version") or "13.0")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cjson"))
        cmake.build()

    def package(self):
        CMake(self).install()
        source = os.path.join(self.source_folder, "cjson")
        copy(self, "LICENSE", source, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", os.path.join(self.source_folder, "luajit"),
             os.path.join(self.package_folder, "licenses", "LuaJIT"))
        copy(self, "test-int64.lua", os.path.join(source, "tests"),
             os.path.join(self.package_folder, "res", "tests"))
        copy(self, "*.adoc", source, os.path.join(self.package_folder, "res", "docs"))
        save(self, os.path.join(self.package_folder, "res", "source.json"),
             json.dumps({"cjson": self.conan_data["sources"][str(self.version)],
                         "luajit_headers": self.conan_data["luajit_headers"]}, indent=2) + "\n")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lua-cjson")
        self.cpp_info.set_property("cmake_target_name", "lua-cjson::lua-cjson")
        self.cpp_info.libs = ["lua-cjson"]
        self.cpp_info.bindirs = []
        if self.settings.os in ("Linux", "FreeBSD", "Android"):
            self.cpp_info.system_libs = ["m"]
