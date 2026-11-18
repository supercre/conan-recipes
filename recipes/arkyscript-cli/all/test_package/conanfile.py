import os
import shlex

from conan import ConanFile


class ArkyscriptCliTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies.build["arkyscript-cli"].package_folder
        examples = os.path.join(package, "res", "examples")
        # 캐시 밖의 작업 디렉터리에서 패키지 안의 엔진과 모듈만으로 실행한다.
        self.run("arky --help")
        for name in ("main.arky", "class.arky", "traits.arky", "async.arky",
                     "modules/main.arky", "imports/main.arky", "tasks/main.arky", "io/files.arky"):
            self.run("arky check " + shlex.quote(os.path.join(examples, name)))
            self.run("arky run " + shlex.quote(os.path.join(examples, name)))
        self.run("arky gen " + shlex.quote(os.path.join(examples, "main.arky")))
