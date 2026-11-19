# Arky Conan 패키지

SDK `0.2.0`의 소스는 `supercre/arkyscript`의 `0f41ae7934afadecf98b05d9caca4db5fcdb8fe8`로 고정한다.
기존 SDK와 CLI `0.1.0`은 `c5ce355048d3baa17f3fe38b138d9142bf8f3aed`를 유지한다.
각 레시피의 `conandata.yml`에서 아카이브 SHA-256도 확인하며, 로컬 체크아웃의 변경은 빌드에 포함하지 않는다.

| 패키지 | 내용 | 플랫폼 |
| --- | --- | --- |
| `arkyscript/0.2.0@sc/dev` | C++20 `binder/*.h`, `*.inl` | 플랫폼 공통 헤더 |
| `arkyscript-cli/0.1.0@sc/dev` | Rust `arky`, 고정 LuaJIT, Task/I/O 모듈, 예제 | 네이티브 macOS/Linux 빌드 |

SDK `0.2.0`의 공개 네임스페이스는 `arky::`다. `arky::state`, `arky::binder`,
`arky::converter<T>`를 사용하며 기존 코드와 변환기 특수화도 함께 옮긴다.
이전 네임스페이스를 사용하는 소비자는 SDK `0.1.0`을 계속 설치할 수 있다.
CLI 버전과 Lua 스크립트 형식은 별도로 관리한다.

클라이언트에는 `arkyscript`를 `requires`로 추가하고 기존 엔진의 LuaJIT를 연결한다.
모바일 앱에 호스트용 컴파일러·별도 LuaJIT가 유입되지 않도록 CLI는 별도 `tool_requires`로 설치한다.
바인더는 LuaJIT 의존성을 직접 추가하지 않으므로 소비자가 LuaJIT 헤더·링크 설정을 제공해야 한다.

```cmake
find_package(arkyscript 0.2.0 CONFIG REQUIRED)
target_link_libraries(game PRIVATE arkyscript::binder)
# game의 기존 LuaJIT 타깃도 연결한다. binder 타깃은 C++20을 요구한다.
```

```sh
conan create recipes/arkyscript/all --version=0.2.0 --user=sc --channel=dev
conan create recipes/arkyscript-cli/all --version=0.1.0 --user=sc --channel=dev --build-require
conan sc:upload arkyscript/0.2.0@sc/dev
conan sc:upload arkyscript-cli/0.1.0@sc/dev

conan sc:install --tool-requires=arkyscript-cli/0.1.0@sc/dev -of build/arky-tools
. build/arky-tools/conanbuild.sh
arky check path/to/main.arky
arky gen path/to/main.arky
arky run path/to/main.arky
```

CLI 소스 빌드에는 Rust 1.94 이상, Python 3.12 이상, Git, Make, C/C++20 컴파일러가 필요하다.
Cargo 의존성은 `--locked`로 유지하며 LuaJIT는 upstream `dependencies.json`의 SHA를 사용한다.
macOS의 기본 최소 실행 버전은 13.0이고 `os.version`을 지정하면 그 값을 사용한다.
CLI는 항상 Release로 빌드하며 package ID는 OS와 아키텍처로 결정한다. 소비자의 C++ 컴파일러
버전이나 Debug/Release 설정 때문에 같은 실행 도구를 다시 빌드하지 않는다.
Windows 및 크로스 컴파일용 CLI 빌드는 현재 레시피에서 명시적으로 거부한다.
헤더 패키지는 Windows/Android/iOS에서도 같은 package ID를 사용한다.

CLI 생성 과정에서 Rust 단위 테스트와 upstream C++ 바인더·Task·I/O 실행 테스트를 수행한다.
`test_package`는 패키지 경로의 예제로 타입 검사, Lua 생성, class/trait, async, 모듈 로딩,
병렬 Task와 파일 I/O를 실행한다. Epic7 어댑터와 앱 검증은 client의 `tests/arky_binding`에서 수행한다.
