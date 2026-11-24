# conan-recipes

SC Conan 레시피 소스와 공개 패키지를 함께 관리하는 저장소.

- **Git (`recipes/`)**: 레시피 코드와 변경 이력
- **[Releases](https://github.com/supercre/conan-recipes/releases)**: 내보낸 레시피와 빌드된 바이너리, 원본 Conan 리비전
- **비공개 SDK**: `supercre/conan-private-package` (FMOD 포함)
- **명령 확장**: 비공개 [supercre/conan-plugin](https://github.com/supercre/conan-plugin)

바이너리 아카이브는 Git/LFS에 커밋하지 않는다. 기존 `supercre/conan-packages` 주소는
이 저장소로 리디렉션된다. 기존 레시피 저장소의 Git 이력도 병합했으며,
원본 저장소는 `supercre/conan-recipes-source-backup`에 보존한다.

Git 소스의 기본 관리 대상은 `@sc/dev` 채널 중 **프리빌트 바이너리 페이로드를 레시피에 포함하지 않는** 레시피다.
Releases에는 기존 버전·채널별 최신 레시피와 package ID별 최신 바이너리를 보관한다.
Git 소스 관리 대상 밖의 레거시 채널도 Releases에서 설치할 수 있다.
추가로 [FMOD `2.02.30@sc/prebuilt`](recipes/fmod/README.md)의 레시피 코드만 관리하며,
FMOD SDK와 패키지 아카이브는 비공개 `supercre/conan-private-package`에 보관한다.
가져온 레시피 파일은 원본 바이트를 유지한다. FMOD의 원래 revision을 재현하려면 별도 SDK 입력도 필요하다.

## 구조

[conan-center-index](https://github.com/conan-io/conan-center-index) 방식을 따른다.

```
recipes/<name>/
  config.yml            # 버전 → 레시피 폴더 매핑
  all/                  # 버전 공통 레시피 (버전별로 내용이 다르면 <version>/ 폴더)
    conanfile.py
    conandata.yml
    patches/
```

## 사용법

```sh
conan sc:update-plugin                   # 기본 저장소를 conan-recipes로 갱신
conan sc:list                            # 공개 패키지 목록
conan sc:list --private                  # 사내 패키지 목록
conan sc:install --requires=zlib/1.3.1@sc/dev --build=missing

python3 scripts/export.py                  # 전체 export (기본 @sc/dev)
python3 scripts/export.py zlib openssl     # 일부 패키지만
python3 scripts/export.py zlib/1.3.1       # 특정 버전만
python3 scripts/export.py zlib --upload    # export 후 이 저장소 Releases에 레시피 게시
conan sc:upload zlib/1.3.1@sc/dev          # 캐시의 레시피와 빌드된 바이너리 게시
```

빌드는 일반적인 Conan 방식으로 한다. 예: `conan create recipes/zlib/all --version 1.3.1 --user sc --channel dev`
기존 Artifactory로 레시피를 올려야 한다면 설정된 리모트를 명시한다:
`python3 scripts/export.py zlib --upload --remote extralib`.
공개 설치는 ConanCenter를 의존성 대체 경로로 사용하며, 사내 의존성도 필요하면 `--with-private`를 지정한다.

## 주의사항

- **줄바꿈 변환 금지**: recipe revision 은 파일 바이트 해시라서 `.gitattributes` 에서 `* -text` 로 변환을 막아 두었다. Windows 에서도 revision 이 바뀌지 않는다.
- **angle, v8**: `build_policy = "never"` 인 export-pkg 전용 레시피이다. `set_version()` 에서 `build.yaml` 을 읽는데, 이 파일은 export 대상이 아니다. `scripts/export.py` 가 버전별로 임시 `build.yaml` 을 만들어 export 한다. 바이너리는 별도 빌드 환경에서 `conan export-pkg` 로 올린다.
- **외부 tool_requires**: libtool, msys2, nasm, gas-preprocessor 는 conancenter 에서 받는다. meson, pkgconf, strawberryperl 은 Releases에 user/channel 없이 올라가 있다.
- **curl 선택 의존성**: c-ares, libidn2, libntlm, libpsl (`@sc/dev`) 은 아직 없다. 기본 옵션에서는 사용하지 않는다.
- **FMOD**: `config.yml`의 `manual_export: true`로 일괄 export에서 제외한다. 별도 SDK를 준비한 뒤 [FMOD 안내](recipes/fmod/README.md)를 따른다.

## Git 소스 관리 대상에서 제외된 것

- `tensorflowlite/2.17@sc/dev`: 레시피에 프리빌트 바이너리(약 1GB)가 포함된 레거시 구조
- `@sc/stable`, `@sc/live-*`, `@sc/prebuilt`, `@sc/release` 등 레거시 채널 (위 FMOD 레시피는 예외)
- user/channel 없는 레퍼런스 (`zlib/1.3.1` 등)

## 레시피 목록

| 패키지 | 버전 |
|---|---|
| angle | 2.1.7219 |
| [arkyscript](recipes/arkyscript/README.md) | 0.1.0, 0.2.0, 0.4.0, 0.5.0, 0.6.0 (C++20 헤더, 0.5.0부터 호스트 런타임 소스) |
| [arkyscript-cli](recipes/arkyscript/README.md) | 0.1.0 (호스트 컴파일러·런타임) |
| astc-encoder | 5.3.0 |
| brotli | 1.1.0 |
| curl | 8.15.0 |
| fdk_aac | 2.0.3 |
| [fmod](recipes/fmod/README.md) | 2.02.30 (`@sc/prebuilt`, 별도 SDK 필요) |
| freetype2 | 2.13.3 |
| glew | 2.2.0 |
| glfw3 | 3.4 |
| jpeg | 2.1.3 |
| ktx | 4.4.2 |
| libuv | 1.51.0 |
| [lua-cjson](recipes/lua-cjson/README.md) | 2.1.0-sc.3 (LuaJIT int64/uint64, 정적 라이브러리) |
| nghttp2 | 1.66.0 |
| nghttp3 | 1.11.0 |
| ngtcp2 | 1.14.0 |
| openh264 | 2.6.0 |
| openssl | 3.5.2 |
| png | 1.6.50 |
| ssr_swc_bridge | 0.1.0 |
| swc_bridge | 0.1.0 |
| swc_native | 1.0.0, 1.0.1, 1.0.2 |
| v8 | 12.4.254.21-patch, 12.4.254.21 |
| webp | 1.0.3 |
| zlib | 1.3.1 |
| zstd | 1.5.7 |
