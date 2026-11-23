import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LuaCjsonTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            runner = os.path.join(self.cpp.build.bindir, "test_package")
            tests = os.path.join(self.dependencies["lua-cjson"].package_folder, "res", "tests")
            # test-compat.lua는 2.1.0-sc.2부터 패키지에 들어 있다.
            for name in ("test-int64.lua", "test-compat.lua"):
                script = os.path.join(tests, name)
                if not os.path.exists(script):
                    continue
                command = f"{shlex.quote(runner)} {shlex.quote(script)}"
                self.run(command, env="conanrun")
                self.run(command + " --joff", env="conanrun")
