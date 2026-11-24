import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LuaJITTest(ConanFile):
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
        # 교차 빌드에서도 링크까지는 확인한다(헤더·라이브러리 이름·아키텍처).
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        runner = os.path.join(self.cpp.build.bindir, "test_package")
        luajit = self.dependencies["luajit"]
        script = os.path.join(luajit.package_folder, "res", "tests", "compat.lua")
        command = f"{shlex.quote(runner)} {shlex.quote(script)}"
        # compat.lua는 beta3와 같은 동작(두 SC 옵션의 기본값)을 검사한다.
        if luajit.options.content_strid and luajit.options.beta3_number_format:
            self.run(command, env="conanrun")
            self.run(command + " --joff", env="conanrun")
        else:
            self.run(shlex.quote(runner), env="conanrun")
