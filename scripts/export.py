#!/usr/bin/env python3
"""recipes/ 아래 레시피를 Conan 캐시로 export (필요 시 업로드).

사용 예:
    python3 scripts/export.py                      # 전체 export
    python3 scripts/export.py zlib openssl         # 일부 패키지만
    python3 scripts/export.py zlib/1.3.1           # 특정 버전만
    python3 scripts/export.py --upload             # export 후 SC GitHub Releases에 게시
    python3 scripts/export.py --upload --remote extralib  # 기존 Conan 리모트로 게시
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "recipes")


def parse_config(path):
    """conan-center-index 형식 config.yml 파싱 (PyYAML 의존성 없이)"""
    entries, version = [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^  "?([^":]+)"?:\s*$', line)
            if m:
                version = m.group(1)
                continue
            m = re.match(r'^    folder:\s*"?([^"\s]+)"?', line)
            if m and version:
                entries.append((version, m.group(1)))
    return entries


def iter_targets(filters):
    for name in sorted(os.listdir(RECIPES)):
        config = os.path.join(RECIPES, name, "config.yml")
        if not os.path.isfile(config):
            continue
        for version, folder in parse_config(config):
            if filters and name not in filters and f"{name}/{version}" not in filters:
                continue
            yield name, version, os.path.join(RECIPES, name, folder)


def requires_manual_export(name):
    """별도 SDK 준비가 필요한 레시피의 명시적 설정을 확인한다."""
    with open(os.path.join(RECIPES, name, "config.yml"), encoding="utf-8") as config:
        return any(re.match(r"^manual_export:\s*true\s*(?:#.*)?$", line) for line in config)


def export(name, version, folder, user, channel):
    # angle, v8 처럼 set_version() 에서 build.yaml 을 읽는 export-pkg 전용 레시피는
    # build.yaml 이 exports 대상이 아니므로, 버전 지정을 위해 임시 파일을 만든다.
    # (manifest 에 포함되지 않으므로 recipe revision 에 영향 없음)
    build_yaml = os.path.join(folder, "build.yaml")
    temp_build_yaml = False
    with open(os.path.join(folder, "conanfile.py")) as f:
        needs_build_yaml = "build.yaml" in f.read()
    if needs_build_yaml and not os.path.exists(build_yaml):
        with open(build_yaml, "w") as f:
            f.write(f'{name}_version: "{version}"\n')
        temp_build_yaml = True
    try:
        cmd = ["conan", "export", folder, "--name", name, "--version", version,
               "--user", user, "--channel", channel]
        return subprocess.run(cmd).returncode == 0
    finally:
        if temp_build_yaml:
            os.remove(build_yaml)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*", help="name 또는 name/version")
    parser.add_argument("--user", default="sc")
    parser.add_argument("--channel", default="dev")
    parser.add_argument("--upload", action="store_true", help="export 후 SC GitHub Releases에 게시")
    parser.add_argument("--remote", help="지정하면 SC GitHub 대신 기존 Conan 리모트로 업로드")
    args = parser.parse_args()

    targets = list(iter_targets(set(args.targets)))
    manual = {name for name, _, _ in targets if requires_manual_export(name)}
    if args.targets and manual:
        names = ", ".join(sorted(manual))
        parser.error(f"{names}: 별도 SDK 준비 후 직접 export해야 합니다. recipes/<name>/README.md를 확인하세요.")

    failed = []
    refs = []
    for name, version, folder in targets:
        if name in manual:
            print(f"건너뜀: {name}/{version} (별도 SDK 준비: recipes/{name}/README.md)", flush=True)
            continue
        ref = f"{name}/{version}@{args.user}/{args.channel}"
        print(f"=== {ref} ({os.path.relpath(folder, ROOT)})", flush=True)
        if export(name, version, folder, args.user, args.channel):
            refs.append(ref)
        else:
            failed.append(ref)

    if args.upload:
        for ref in refs:
            if args.remote:
                command = ["conan", "upload", ref, "-r", args.remote, "--only-recipe", "-c"]
            else:
                command = ["conan", "sc:upload", ref, "--only-recipe"]
            if subprocess.run(command).returncode:
                failed.append(ref)

    if failed:
        print("실패:", *failed, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()
