# FMOD 레시피

`fmod/2.02.30@sc/prebuilt`의 레시피 코드를 관리한다.
`extralib`와 비공개 `supercre/conan-private-package`에 게시된
레시피 리비전 `077125d4fcec1233c2ee96cbbaacd38b`의 `conanfile.py`를 원본 바이트 그대로 가져왔다.
기존 패키지 ID 계산과 파일 배치, CMake 컴포넌트 설정을 유지한다.

이 Git 폴더에는 레시피 코드와 설정·문서만 저장한다.
FMOD SDK 입력, SDK가 포함된 Conan 레시피 아카이브와 바이너리는
[비공개 패키지 저장소](https://github.com/supercre/conan-private-package)에서 관리한다.

## 기존 패키지 사용

SC 확장 설치와 GitHub 인증을 마친 개발자는 프로젝트의 `conanfile.txt` 또는
`conanfile.py`에 `fmod/2.02.30@sc/prebuilt`를 추가한 뒤 설치한다.

```bash
conan sc:list 'fmod/*:*' --private
conan sc:install . --with-private --build=never
```

호스트 프로필은 게시된 패키지의 OS·아키텍처·컴파일러 설정과 맞아야 한다.
비공개 패키지는 사내 개발에 필요한 헤더와 라이브러리, 플랫폼별 부속 파일을 함께 제공한다.

## 레시피 수정 및 export

사내 SDK 입력을 `all/` 아래에 준비한다. 이 디렉터리들은 `.gitignore`로 제외된다.

```text
all/
├── conanfile.py
├── android/
│   ├── fmod.jar
│   └── <ABI>/include/, lib/
├── ios/arm64/include/, lib/
└── windows/x64/include/, lib/, bin/
```

`exports_sources`는 `android/*`, `ios/*`, `windows/*`를 포함한다.
SDK 없이 export하면 원래 레시피 리비전을 재현할 수 없고, 필요한 파일이 없는 패키지가 생길 수 있다.
`config.yml`의 `manual_export: true`로 일괄 `scripts/export.py` 실행에서 제외한다.
직접 대상을 지정해도 해당 스크립트는 별도 준비 절차를 안내하며 중단한다.

SDK를 준비한 뒤 저장소 루트에서 실행한다.

```bash
conan export recipes/fmod/all --user=sc --channel=prebuilt
```

바이너리를 새로 패키징하려면 같은 레시피에 `conan create`와 대상 플랫폼의 프로필을 사용한다.
이 레시피는 제공된 SDK를 패키징하며 FMOD 엔진 자체를 재컴파일하지 않는다.
생성된 레시피·바이너리는 `conan sc:upload 'fmod/2.02.30@sc/prebuilt' --private`로 게시한다.

현재 Git에 추가한 것은 `2.02.30@sc/prebuilt` 레시피다. 다른 버전·채널 및 `fmod_shared`는 포함하지 않는다.
