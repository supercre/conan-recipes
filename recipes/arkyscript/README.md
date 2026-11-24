# Arky Conan 패키지

SDK `0.6.0`의 소스는 `supercre/arkyscript`의 `83656750b1bbf727bd4fe0840ae049e3a8ff1138`로,
`0.5.0`은 `f6380d619e1e037c9e597ed7b14825beb32003d7`로, `0.4.0`은 `84bbe16c076b1b0b25b1dd4b70a505f3d2254d9a`로 고정한다.
`0.6.0`에서는 `require`로 불러온 Arky 모듈이 런타임 환경을 스스로 쓴다(정적 import를 미리 준비하지 않아도 된다).
같은 커밋의 컴파일러가 만든 모듈은 이 런타임을 전제로 하므로 `0.5.0`에서는 `unprepared static import` 오류가 난다.
`0.5.0`에는 호스트 런타임 소스가 더 들어 있고, step 밖에서 만든 `scheduler.sleep` 타이머가
다음 step부터 세도록 고친 스케줄러가 들어 있다.
SDK `0.2.0`은 `0f41ae7934afadecf98b05d9caca4db5fcdb8fe8`, SDK와 CLI `0.1.0`은
`c5ce355048d3baa17f3fe38b138d9142bf8f3aed`를 유지한다. `0.3.0`은 게시하지 않은 번호다.
각 레시피의 `conandata.yml`에서 아카이브 SHA-256도 확인하며, 로컬 체크아웃의 변경은 빌드에 포함하지 않는다.

| 패키지 | 내용 | 플랫폼 |
| --- | --- | --- |
| `arkyscript/0.6.0@sc/dev` | C++20 `binder/*.h`, `*.inl`, 호스트 런타임 `runtime/` 소스 | 플랫폼 공통 헤더·소스 |
| `arkyscript-cli/0.1.0@sc/dev` | Rust `arky`, 고정 LuaJIT, Task/I/O 모듈, 예제 | 네이티브 macOS/Linux 빌드 |

SDK `0.2.0`의 공개 네임스페이스는 `arky::`다. `arky::state`, `arky::binder`,
`arky::converter<T>`를 사용하며 기존 코드와 변환기 특수화도 함께 옮긴다.
이전 네임스페이스를 사용하는 소비자는 SDK `0.1.0`을 계속 설치할 수 있다.
CLI 버전과 Lua 스크립트 형식은 별도로 관리한다.

SDK `0.4.0`은 `0.2.0` 이후의 바인더 변경을 담는다. `0.2.0`의 API는 그대로 쓸 수 있다.

- 이름으로 등록하는 네이티브 클래스(`binder/lua_named_class.h`): C++ 타입 대신 이름으로 클래스를
  등록하고, 멤버 함수·속성·자유 함수를 인자 타입으로 등록한다(typed 등록). 여러 값과 나머지 인자,
  컨테이너, 여러 반환값을 받는다.
- 객체의 소유권과 수명 규칙: 만료된 객체에 대한 native 호출을 막는 정책을 고를 수 있다.
- Windows: `/EHsc`로 빌드한 호스트에서 변환 실패 같은 Lua 오류가 프로세스를 끝내던 문제를 고쳤다.
  MSVC로도 이름 기반 typed 등록을 컴파일할 수 있다.

자세한 규칙은 패키지의 `res/binder/README.md`에 있다.

SDK `0.5.0`부터 호스트 임베딩 런타임(`arky::runtime`: async/await 스케줄러, 타이머, worker Task,
파일·TCP I/O, 정적 import)을 소스로 넣는다. 호스트는 `include/runtime/arky_runtime.cpp` 한 파일을
자기 LuaJIT와 함께 C++20으로 컴파일한다. 경로는 패키지의 CMake 모듈이 `ARKYSCRIPT_RUNTIME_SOURCE`로 알려 준다.
Windows는 `ws2_32`를 함께 링크한다. 사용법은 패키지의 `res/runtime/embedding.md`에 있다.

```cmake
find_package(arkyscript 0.6.0 CONFIG REQUIRED)
target_sources(game PRIVATE "${ARKYSCRIPT_RUNTIME_SOURCE}")
target_link_libraries(game PRIVATE arkyscript::binder)
```

클라이언트에는 `arkyscript`를 `requires`로 추가하고 기존 엔진의 LuaJIT를 연결한다.
모바일 앱에 호스트용 컴파일러·별도 LuaJIT가 유입되지 않도록 CLI는 별도 `tool_requires`로 설치한다.
바인더는 LuaJIT 의존성을 직접 추가하지 않으므로 소비자가 LuaJIT 헤더·링크 설정을 제공해야 한다.

```cmake
find_package(arkyscript 0.6.0 CONFIG REQUIRED)
target_link_libraries(game PRIVATE arkyscript::binder)
# game의 기존 LuaJIT 타깃도 연결한다. binder 타깃은 C++20을 요구한다.
```

```sh
conan create recipes/arkyscript/all --version=0.6.0 --user=sc --channel=dev
conan create recipes/arkyscript-cli/all --version=0.1.0 --user=sc --channel=dev --build-require
conan sc:upload arkyscript/0.6.0@sc/dev
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
