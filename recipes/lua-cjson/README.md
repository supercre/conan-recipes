# Lua CJSON: LuaJIT 64비트 정수 지원

`lua-cjson/2.1.0-sc.3@sc/dev`는 `supercre/lua-cjson`의
`225cf5693ad6eb854c211466839d5a2db5a9f39d`를 고정한 정적 라이브러리다.
이전 버전 `2.1.0-sc.2`(`9a1a337a11b51c23f666cd44043fce23a34b35f7`)와
`2.1.0-sc.1`(`b51521934424bd9a74ea3dd7a8f5a89b3b1fc7e9`)도 그대로 설치할 수 있다.
Windows(MSVC)에서는 `2.1.0-sc.3`부터 빌드된다. [Windows](#windows) 참고.
Conan 버전은 SC 포크 버전이고 upstream의 `cjson._VERSION`은 `2.1devel`로 유지한다.

LuaJIT의 공개 Lua 5.1 ABI 헤더만 빌드에 사용한다. 런타임과 Lua 헤더를 패키지에
중복 포함하지 않으므로 게임 엔진이 사용하는 LuaJIT를 함께 연결해야 한다.
Lua 5.2 이상과는 ABI가 다르며, 64비트 cdata 기능에는 LuaJIT FFI가 필요하다.

## 설치 및 연결

```sh
conan sc:install --requires=lua-cjson/2.1.0-sc.3@sc/dev --build=missing \
  -g CMakeDeps -g CMakeToolchain -of build/conan
```

```cmake
find_package(lua-cjson CONFIG REQUIRED)
target_link_libraries(game PRIVATE lua-cjson::lua-cjson luajit)
```

`luajit`은 소비자 프로젝트의 기존 런타임 타깃이다. 헤더 `lua_cjson.h`에서 제공하는
`luaopen_cjson`과 `luaopen_cjson_safe`를 같은 Lua 상태의 `package.preload`에 등록한다.

```c
lua_getglobal(L, "package");
lua_getfield(L, -1, "preload");
lua_pushcfunction(L, luaopen_cjson);
lua_setfield(L, -2, "cjson");
lua_pushcfunction(L, luaopen_cjson_safe);
lua_setfield(L, -2, "cjson.safe");
lua_pop(L, 2);
```

```lua
local json = require "cjson"
json.decode_int64("always")
assert(json.encode(json.decode("9223372036854775807")) == "9223372036854775807")
assert(json.encode(18446744073709551615ULL) == "18446744073709551615")
```

기본 디코딩 모드는 `off`이고 `auto`는 안전 정수 범위를 넘는 값만 cdata로 반환한다.
범위를 넘는 10진 정수는 활성화된 모드에서 오류다. 소수점/지수 표기는 Lua number로 유지한다.

## 기존 엔진 호환 설정

`2.1.0-sc.2`부터 설정 두 개가 있다. 기본값은 둘 다 `false`이고 `cjson.new()`로 만든 인스턴스마다 따로 정한다.
엔진에 내장해 쓰던 cocos2d-x 계열 cjson과 같은 동작이 필요하면 모듈을 연 뒤 둘 다 켠다.

```lua
json.decode_lua_nil(true)          -- JSON null을 cjson.null 대신 Lua nil로 읽는다
json.decode_invalid_escapes(true)  -- "\q"처럼 규격에 없는 이스케이프를 오류 없이 뒤의 문자로 읽는다
assert(json.decode('{"a":null}').a == nil)
assert(json.decode([["a\qb"]]) == "aqb")
```

## Windows

`2.1.0-sc.2`까지는 MSVC로 빌드되지 않았다. 포크의 CMake가 `snprintf`를 `_snprintf` 매크로로
정의했고, VS2015부터의 C 런타임(UCRT)은 `<stdio.h>`에서 이를 오류(C1189)로 막는다.
`2.1.0-sc.3`은 그 정의를 예전 C 런타임(VS2013 이하)에서만 쓴다.

같은 조건에서 Windows 빌드에만 걸려 있던 `DISABLE_INVALID_NUMBERS`도 풀었다. `2.1.0-sc.3`의
Windows 빌드는 다른 플랫폼처럼 `01`, `+1`, `0x10`, `NaN`, `Infinity`를 숫자로 디코딩한다.
이전에는 Windows에서만 이 입력이 오류였다.

## 빌드 및 검증

```sh
conan create recipes/lua-cjson/all --version=2.1.0-sc.3 --user=sc --channel=dev \
  -s compiler.version=21.0
conan sc:upload lua-cjson/2.1.0-sc.3@sc/dev
```

현재 게시한 바이너리는 macOS arm64, Apple Clang 21.0의 Release/Debug와
Windows x86_64, MSVC 194(동적 런타임)의 Release/Debug이다. Windows 바이너리는 macOS에서
clang-cl(MSVC ABI)로 크로스 빌드했다. Visual Studio 18(cl 19.51)의 CMake 빌드에서
`tests/test.lua`, `test-int64.lua`, `test-compat.lua`가 통과하는 것은 따로 확인했다.
macOS 최소 배포 버전의 기본값은 13.0이고, `os.version`을 지정하면 해당 값을 사용한다.
현재 툴체인과 다른 기본 프로파일은 그대로 유지하고 설치 시 해당 설정을 명시한다.

```sh
conan sc:install --requires=lua-cjson/2.1.0-sc.3@sc/dev \
  -s compiler.version=21.0 --build=never
```

다른 플랫폼/툴체인은 `--build=missing`으로 소스에서 빌드한다. 해당 플랫폼의 실행 검증은 별도다.
정적 라이브러리 자체는 고정된 LuaJIT 소스에서 헤더를 받아 빌드하며 시스템 LuaJIT가 필요 없다.
`test_package`를 실행할 때는 시스템 LuaJIT와 pkg-config가 필요하다.
패키지의 라이브러리를 실제 소비자 실행 파일에 연결하여 int64 검증 10,414개와
호환 설정 검증 47개를 JIT on/off로 실행한다.
