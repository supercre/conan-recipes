# conan-recipes

[extralib](https://conan.supercreative.kr:27443/artifactory/api/conan/extralib) Conan 리모트에 올라가는 레시피를 관리하는 저장소.

현재는 `@sc/dev` 채널 중 **프리빌트 바이너리 페이로드를 레시피에 포함하지 않는** 레시피만 관리한다.
각 레시피는 extralib 에 올라가 있는 최신 revision 과 동일한 내용이다 (재-export 시 revision 해시 일치 확인됨).

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
conan remote add extralib https://conan.supercreative.kr:27443/artifactory/api/conan/extralib

python3 scripts/export.py                  # 전체 export (기본 @sc/dev)
python3 scripts/export.py zlib openssl     # 일부 패키지만
python3 scripts/export.py zlib/1.3.1       # 특정 버전만
python3 scripts/export.py zlib --upload    # export 후 extralib 로 레시피 업로드
```

빌드는 일반적인 Conan 방식으로 한다. 예: `conan create recipes/zlib/all --version 1.3.1 --user sc --channel dev`

## 주의사항

- **줄바꿈 변환 금지**: recipe revision 은 파일 바이트 해시라서 `.gitattributes` 에서 `* -text` 로 변환을 막아 두었다. Windows 에서도 revision 이 바뀌지 않는다.
- **angle, v8**: `build_policy = "never"` 인 export-pkg 전용 레시피이다. `set_version()` 에서 `build.yaml` 을 읽는데, 이 파일은 export 대상이 아니다. `scripts/export.py` 가 버전별로 임시 `build.yaml` 을 만들어 export 한다. 바이너리는 별도 빌드 환경에서 `conan export-pkg` 로 올린다.
- **외부 tool_requires**: libtool, msys2, nasm, gas-preprocessor 는 conancenter 에서 받는다. meson, pkgconf, strawberryperl 은 extralib 에 user/channel 없이 올라가 있다.
- **curl 선택 의존성**: c-ares, libidn2, libntlm, libpsl (`@sc/dev`) 은 아직 없다. 기본 옵션에서는 사용하지 않는다.

## 관리 대상에서 제외된 것

- `tensorflowlite/2.17@sc/dev`: 레시피에 프리빌트 바이너리(약 1GB)가 포함된 레거시 구조
- `@sc/stable`, `@sc/live-*`, `@sc/prebuilt`, `@sc/release` 등 레거시 채널
- user/channel 없는 레퍼런스 (`zlib/1.3.1` 등)

## 레시피 목록

| 패키지 | 버전 |
|---|---|
| angle | 2.1.7219 |
| astc-encoder | 5.3.0 |
| brotli | 1.1.0 |
| curl | 8.15.0 |
| fdk_aac | 2.0.3 |
| freetype2 | 2.13.3 |
| glew | 2.2.0 |
| glfw3 | 3.4 |
| jpeg | 2.1.3 |
| ktx | 4.4.2 |
| libuv | 1.51.0 |
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
