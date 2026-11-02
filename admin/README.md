# MIRAE PASS DASHBOARD
---
미래 패스 서비스의 관리자 시스템

## 🔒 개발 환경설정
---
```bash
# Git clone
git clone https://git.rldn.xyz/scfs.miraepass/dashboard.git
cd front

# 필요 라이브러리 설치및 환경 구성
yarn install

# 개발 환경 실행
yarn dev
```

## ✨ 명령어 및 개발 가이드
---
`http://localhost:8000/openapi.json`는 백엔드 서버의 openapi.json 파일입니다. 개발시 주소가 다를 경우 주소를 수정해주세요.
### SDK 생성
```bash
npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o app/sdk -c @hey-api/client-ofetch
```

### 버전 지정
버전의 경우 package.json에 작성합니다.<br>
Dev또는 Master 브랜치에 푸시될경우 [semantic-release](https://github.com/semantic-release/semantic-release)를 통해 자동으로 버전이 지정되로 릴리즈 됩니다.
```
Major.Minor.Patch
- Major (1.x.x): 기존 기능과 호환되지 않는 큰 변화가 있을 때 (예: UI 전면 개편)
- Minor (x.1.x): 새로운 기능이 추가되었지만, 기존 기능은 그대로 잘 작동할 때
- Patch (x.x.1): 단순한 버그 수정이나 성능 개선이 있었을 때
```

### 커밋 메시지
기본적으로 [Conventional Commits](https://www.conventionalcommits.org/ko/v1.0.0/)를 사용합니다.
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

#### Type
- feat: 새로운 기능 추가 (버전 Minor의 영향)
- fix: 버그 수정 (버전 Patch의 영향)
- perf: 성능 개선 (버전 Patch의 영향)
- docs: 문서만 수정했을 때 (README, 주석 추가 등)
- style: 코드 의미에 영향을 주지 않는 변경사항 (들여쓰기, 세미콜론 누락, 포맷팅 수정 등)
- refactor: 코드 구조 개선
- test: 테스트 코드를 추가/수정
- build: 빌드 시스템이나 외부 의존성에 변화
- ci: CI 설정이나 스크립트 수정
- chore: 패키지 매니저 설정이나 작업, 빌드와는 관계없는 자잘한 작업
- revert: 커밋을 되돌림

#### Scope
- sdk: API SDK 관련
- ui: 프론트 화면, 컴포넌트 관련

## 📦 프로젝트 구조
---
```
...
```


## 🛠 기술 스택
---
- Framework: Nuxt.js
- CSS Framework: TailwindCSS
- Nuxt Modules: ...
- Package Management: Yarn