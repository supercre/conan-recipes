# LuaJIT 2.1: 2.1.0-beta3 호환 정적 라이브러리

`luajit/2.1.1795119671-sc.1@sc/dev`는 LuaJIT `v2.1` 브랜치의
`96f7b297326e9fd454b7186c6858b2773f94a0dc`(2026-11-19)를 고정하고 SC 패치를 더한 정적 라이브러리다.
`lua-cjson/2.1.0-sc.3`이 헤더를 받는 커밋과 같다.

- **버전:** 앞부분은 업스트림 롤링 버전으로 `jit.version`(`LuaJIT 2.1.1795119671`)과 같다.
  뒤의 `-sc.N`은 SC 패치 판이다. 같은 업스트림 커밋에서 패치만 바꾸면 `-sc.2`로 올린다.
- **주의:** ConanCenter의 `luajit/2.1.<시각>`은 같은 버전 체계를 쓰는 패치 없는 업스트림 빌드다.
  `-sc.N`과 `@sc/dev`가 없는 버전으로 바꾸면 `pairs` 순서와 반올림이 beta3와 달라지지만 빌드는 그대로 통과한다.

기존 사내 패키지(`luajit/2.1.0-beta3@sc/live-0.0.3`, iOS는 `live-0.0.2`)를 대체한다.
기존 패키지는 미리 빌드한 바이너리를 복사만 했다. iOS 바이너리는 실제로 2.1.0-beta2(2016)였다.
Windows 바이너리만 Lua 5.2 확장을 켜고 정적 C 런타임(`/MT`)으로 빌드돼 있었다.

## SC 패치와 옵션

기본값은 모두 2.1.0-beta3와 같은 동작을 낸다. 같은 스크립트를 실행할 때 기존 클라이언트, 서버의 전투 검증
(arena_server는 beta3, play_server는 2025-01 롤링 버전)과 결과가 같아야 하기 때문이다.

| 옵션 | 기본값 | 내용 |
|---|---|---|
| `content_strid` | `True` | 문자열 키의 테이블 위치를 내용 해시로 정한다(`patches/0001`). |
| `beta3_number_format` | `True` | 숫자 출력의 반올림을 beta3처럼 0.5에서 올림으로 한다(`patches/0002`). |
| `lua52compat` | `False` | Lua 5.2 확장(`table.pack`, `__pairs`, `__len` 등). Android·iOS와 같게 끈다. |
| `fPIC` | `True` | Windows 외 플랫폼. |

Windows 외 플랫폼은 옵션과 관계없이 `-ffp-contract=off`로 빌드한다.

### content_strid

LuaJIT는 2020-06(`ff34b48d`)부터 문자열 키의 테이블 위치를 "문자열 ID"로 정한다. 이 ID는 내용이 아니라
VM 안에서 문자열이 만들어진 순서로 붙는다. 그래서 같은 코드라도 다음과 같이 된다.

- `pairs`가 문자열 키를 도는 순서가 그 VM에서 먼저 만든 문자열에 따라 바뀐다.
- 기본 보안 설정(`LUAJIT_SECURITY_STRID=1`)에서는 실행할 때마다 바뀐다.
- 어느 설정이든 beta3와 다르다.

`LUAJIT_SECURITY_*` 플래그로는 beta3의 순서를 되돌릴 수 없다.

패치는 문자열 ID를 시드 없는 sparse 해시로 정한다. beta3가 테이블 위치에 쓰던 해시와 같은 함수다.
테이블 코드, 인터프리터와 JIT 기계어가 모두 이 ID를 읽으므로 이 한 곳만 바꾼다.
파서도 이 ID를 변수 이름의 해시 버킷으로만 쓴다(이름 비교는 포인터로 한다).
대신 업스트림이 2020년에 넣은 해시 충돌 공격 방어는 beta3 수준으로 돌아간다.

확인한 내용(맥에서 2.1.0-beta3를 x86_64 GC64로 빌드해 Rosetta로 비교):

- 표 383개의 `pairs` 순서가 beta3 인터프리터와 모두 같다.
- 실행 이력을 바꿔도(무관한 문자열 500개를 먼저 만듦) 같고, JIT를 켜도 같다.
- 패치하지 않은 빌드는 336개가 다르고, 실행할 때마다 달라진다.
- 2.1.0-beta2도 beta3와 같은 순서다.

### beta3_number_format

업스트림 `7152e154`(2025-12)는 고정 자릿수 숫자 출력을 짝수 반올림으로 바꿨다. 영향을 받는 것은
`string.format`의 `%.Nf`·`%e`·`%g`와 `tostring`(`%.14g`)이다. 예를 들면 다음과 같다.

- `string.format('%.0f', 2.5)`: beta3는 `3`, 업스트림은 `2`
- `tostring(90422959341864.5)`: beta3는 `90422959341865`, 업스트림은 `90422959341864`

맥에서 비교한 결과다.

- 고정 자릿수 출력 22만 8천 개 중 1,283개가 달랐다.
- `tostring`·`%g`·`%e` 출력 27만 개 중 9,039개가 달랐다.
- 패치를 켜면 두 비교 모두 beta3와 같다.

패치는 그 커밋 이전의 반올림(5×10^e를 더하는 방식)을 조건부로 되돌린다.

### -ffp-contract=off

최근 Clang(NDK 29, Xcode 27)은 arm64에서 C 코드의 `a*b+c`를 FMA 명령 하나로 합친다.
`lib_math.c`의 난수 시드 계산이 이렇게 컴파일되면, `math.randomseed(n)` 뒤의 `math.random` 값이
x64와 기존 Android 빌드(NDK clang 9, FMA 없음)와 달라진다. JIT는 FMA를 기본으로 쓰지 않는다
(업스트림 `de2e1ca9`). 빌드한 Android·iOS·macOS 라이브러리에 FMA 명령이 없는 것을 `llvm-objdump`로 확인했다.

### 그 밖에 beta3와 다른 점

비교 스크립트(표준 라이브러리 128개 항목)에서 남은 차이는 다음뿐이다.

- `math.randomseed()`를 인자 없이 부를 수 있다. beta3는 오류다.
- `require 'string.buffer'`가 있다.
- 3.0 문법 일부를 받는다(`5 & 3`, `7 // 2` 등). 이 문법은 beta2·beta3에서 구문 오류다.
  구버전 앱이 남아 있는 동안 스크립트에 쓰면 안 된다.

## 설치 및 연결

```sh
conan sc:install --requires=luajit/2.1.1795119671-sc.1@sc/dev --build=missing \
  -g CMakeDeps -g CMakeToolchain -of build/conan
```

```cmake
find_package(luajit CONFIG REQUIRED)
target_link_libraries(game PRIVATE luajit::luajit)
```

헤더는 `include/luajit-2.1`에 있고 이 폴더가 include 경로다(`#include "lua.h"`).
라이브러리는 Windows가 `lua51.lib`, 그 밖이 `libluajit.a`다.

교차 빌드가 아니면 `bin/`에 `luajit` 실행 파일이 함께 들어간다. 바이트코드 저장(`luajit -b`)에 쓰는
`jit/*.lua`는 `bin/lua/jit`에 있다. Windows는 기본 검색 경로가 이 자리이고, 그 밖의 플랫폼은
Conan 환경의 `LUA_PATH`로 찾는다.

## 빌드

Linux 바이너리는 macOS에서 Apple `container`로 Ubuntu 24.04를 띄워 그 안에서 빌드한다(레시피는 Linux에서 그대로 빌드된다).

```sh
container system start
container run --rm -v <recipe-and-script>:/work ubuntu:24.04 /work/build.sh                       # arm64
container run --rm --platform linux/amd64 --rosetta -v <...>:/work ubuntu:24.04 /work/build.sh   # x86_64
```

`build.sh`는 gcc와 Conan 2.27.1을 설치하고 `conan create`(Release/Debug)를 한 뒤 `conan cache save`로 결과를 내보낸다.
macOS에서 `conan cache restore`로 받아 `conan sc:upload`한다.

LuaJIT의 Makefile(macOS, iOS, Android, Linux)과 `msvcbuild.bat`(Windows)를 그대로 쓴다.
`buildvm`이 대상과 같은 포인터 크기로 호스트에서 돌아야 하므로 64비트 대상(`armv8`, `x86_64`)만 받는다.

```sh
# macOS
conan create recipes/luajit/all --version=2.1.1795119671-sc.1 --user=sc --channel=dev -s compiler.version=21.0

# Android: 클라이언트(yuna_toolchain.cmake)가 쓰는 설정과 같다
conan create recipes/luajit/all --version=2.1.1795119671-sc.1 --user=sc --channel=dev \
  -pr:b default -s:h os=Android -s:h os.api_level=26 -s:h arch=armv8 -s:h compiler=clang \
  -s:h compiler.version=17 -s:h compiler.libcxx=c++_static -s:h compiler.cppstd=20 \
  -c:h tools.android:ndk_path=$ANDROID_HOME/ndk/29.0.13846066

# iOS: xcode-select가 Command Line Tools를 가리키면 iOS SDK를 찾지 못한다
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer conan create recipes/luajit/all \
  --version=2.1.1795119671-sc.1 --user=sc --channel=dev -pr:b default -s:h os=iOS \
  -s:h os.sdk=iphoneos -s:h os.version=13.0 -s:h arch=armv8 -s:h compiler=apple-clang \
  -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h compiler.cppstd=20
```

Windows 바이너리는 Visual Studio가 있는 Windows에서만 빌드한다. `msvcbuild.bat static`에
소비자와 같은 C 런타임(`/MD`·`/MDd`)과 `/Z7`을 `_CL_` 환경 변수로 넘긴다. 맥에서 하는 Windows
크로스 빌드(클라이언트의 `WindowsCrossConan.cmake`, `--build=never`)는 게시된 바이너리를 받아야 한다.
클라이언트는 VS 18로 빌드하지만 Conan 설정은 msvc 194다. 게시 바이너리는 VS 18에 함께 설치된
14.44 툴셋으로 만들어 설정과 실제 컴파일러를 맞춘다(새 링커는 이전 툴셋의 오브젝트를 링크한다).

```bat
conan create recipes/luajit/all --version=2.1.1795119671-sc.1 --user=sc --channel=dev ^
  -s arch=x86_64 -s compiler=msvc -s compiler.version=194 -s compiler.runtime=dynamic ^
  -s compiler.runtime_type=Release -s build_type=Release -s compiler.cppstd=20 ^
  -c tools.microsoft.msbuild:vs_version=18 -c tools.cmake.cmaketoolchain:generator=Ninja
```

ARM64 Windows에서는 `-s:b arch=x86_64`를 더해 x64 호스트 도구로 빌드한다. 그러지 않으면 Conan이
교차 빌드로 보고 test_package 실행과 `luajit.exe` 패키징을 건너뛴다.

## 바이너리

클라이언트(`yuna_toolchain.cmake`의 `install_conan`)가 실제로 요구하는 설정으로 만든다.
설정이 하나라도 다르면 `--build=missing`으로 소스에서 빌드한다.

| 플랫폼 | 설정 |
|---|---|
| Android | arm64·x86_64, clang 17, `os.api_level` 24(클라이언트)와 26, Release/Debug |
| iOS | 기기·시뮬레이터 arm64, apple-clang 15, `os.version` 13.0, Release/Debug |
| macOS | arm64, apple-clang 15(클라이언트), 15 + `os.version` 13.0(dev-publisher), 21.0, Release/Debug |
| Windows | x86_64, msvc 194, 동적 런타임, Release/Debug |
| Windows arm64 | armv8, msvc 195(VS 18의 14.5 툴셋), 동적 런타임, Release/Debug. VS 18의 14.44 툴셋에는 ARM64 대상이 없다 |
| Linux | x86_64·armv8, gcc 13(Ubuntu 24.04), Release/Debug |

## 검증

`res/tests/compat.lua`가 패키지에 들어 있다. test_package는 이 스크립트를 JIT를 켜고/끄고 실행한다.
기기에서도 같은 파일을 실행하면 된다. 검사 항목은 다음과 같다.

1. 문자열 키의 `pairs` 순서가 beta3 기대값과 같다.
2. 그 순서가 실행 이력과 무관하다.
3. 게임 전투 난수기(`script/libs/luautil.lua`의 `getRandom`)가 beta3 인터프리터와 같은 수열을 낸다.
   2.1.0-beta3를 최신 Clang으로 빌드하면 JIT가 이 계산을 틀리게 해서(X1이 음수가 된다) 이 항목에서 실패한다.
   업스트림은 2025-11에 C 코드에서 고쳤다(`1acb2044`).
4. `string.format`·`tostring`의 반올림이 beta3와 같다.
5. `math.random`의 시드 계산이 x64와 같다.

2026-11-24에 확인한 범위는 다음과 같다.

| 플랫폼 | 구성 | 확인 |
|---|---|---|
| macOS arm64 | Apple Clang 21, Release/Debug | `conan create`, test_package 실행(JIT 켬/끔) 통과 |
| Windows x64 | VS 18의 14.44 툴셋(msvc 194), `/MD`·`/MDd` | `conan create`, test_package 실행(JIT 켬/끔) 통과. 19.51 툴셋으로도 같은 결과 |
| Windows arm64 | VS 18의 14.5 툴셋(msvc 195), `/MD`·`/MDd` | ARM64 Windows에서 `conan create`, test_package 실행(JIT 켬/끔) 통과 |
| Linux x86_64·arm64 | Ubuntu 24.04, gcc 13 | macOS의 Apple `container`로 띄운 Ubuntu에서 `conan create`, test_package 실행(JIT 켬/끔) 통과. x86_64는 Rosetta로 실행 |
| Android arm64·x86_64 | NDK 29, API 26, Release/Debug | `conan create`, test_package 링크까지. 실행은 하지 않았다. |
| iOS 기기·시뮬레이터 arm64 | Xcode 27 SDK, iOS 13.0, Release/Debug | `conan create`, test_package 링크까지. 실행은 하지 않았다. |
