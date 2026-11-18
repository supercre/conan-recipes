import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import chdir, copy, get, load, save


class ArkyscriptCliConan(ConanFile):
    name = "arkyscript-cli"
    package_type = "application"
    description = "Arky compiler and pinned LuaJIT, Task and I/O runtime"
    url = "https://github.com/supercre/conan-recipes"
    homepage = "https://github.com/corbie79/arkyscript"
    # 도구와 동적 모듈을 함께 배포하므로 소비자 C++ ABI/Debug 설정과 분리한다.
    settings = "os", "arch"

    def validate(self):
        if self.settings.os not in ("Macos", "Linux") or cross_building(self):
            raise ConanInvalidConfiguration("arkyscript-cli requires a native macOS/Linux build")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], filename="source.tar.gz", strip_root=True)

    def build(self):
        python = shlex.quote(sys.executable)
        environment = Environment()
        if self.settings.os == "Macos":
            # LuaJIT와 C++ 모듈이 빌드 머신의 최신 OS를 최소 버전으로 기록하지 않게 한다.
            environment.define("MACOSX_DEPLOYMENT_TARGET", str(self.settings.os.get_safe("version") or "13.0"))
        with environment.vars(self).apply(), chdir(self, self.build_folder):
            self.run("cargo build --release --locked -p tynex-cli")
            self.run(f'{python} -c "import sys; sys.path.insert(0, \'scripts\'); '
                     'from bootstrap import build_native; build_native()"')
            self.run(f"{python} scripts/build_task.py")
            if not self.conf.get("tools.build:skip_test", default=False, check_type=bool):
                self.run("cargo test --workspace --locked")
                self.run(f"{python} scripts/test_binder.py")

    def package(self):
        destination = os.path.join(self.package_folder, "bin")
        copy(self, "arky", os.path.join(self.build_folder, "target", "release"), destination)
        revision = json.loads(load(self, os.path.join(self.build_folder, "dependencies.json")))["luajit"]["revision"]
        engine = os.path.join(self.build_folder, "build", "native", revision)
        for name in ("luajit", "tynex_task.so", "tynex_io.so"):
            copy(self, name, os.path.join(engine, "src"), destination)
        copy(self, "*.lua", os.path.join(engine, "src", "jit"), os.path.join(destination, "jit"))
        copy(self, "COPYRIGHT", engine, os.path.join(self.package_folder, "licenses", "LuaJIT"))
        copy(self, "*", os.path.join(self.build_folder, "examples"),
             os.path.join(self.package_folder, "res", "examples"))
        copy(self, "dependencies.json", self.build_folder, os.path.join(self.package_folder, "res"))
        copy(self, "Cargo.lock", self.build_folder, os.path.join(self.package_folder, "res"))
        save(self, os.path.join(self.package_folder, "res", "source.json"),
             json.dumps(self.conan_data["sources"][str(self.version)], indent=2) + "\n")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
