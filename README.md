# MIRAEPASS
새로운 미래패스 모노레포, 작업중 입니다.

```
MIRAE-PASS
  client      // 기존 'Front'
  admin       // 기존 'Dashboard'
  server      // 기존 'Backend'
  docs        // 관련 문서
  api-client  // SDK
```

## 개발 환경
`client`, `admin`, `api-client`는 Yarn 4 워크스페이스입니다. 의존성은 저장소 루트에서 설치하며 `yarn.lock`도 루트에 하나만 둡니다.
Yarn 버전은 `package.json`의 `packageManager`로 고정되어 있으므로 Corepack을 한 번 활성화해야 합니다.
`server`는 워크스페이스에 포함되지 않고 `uv`로 따로 관리합니다. [server/README.md](server/README.md)를 참고하세요.

```bash
corepack enable
yarn install

yarn dev:client         # 또는 dev:admin
yarn build:client       # 또는 build:admin
yarn typecheck:client   # 또는 typecheck:admin
```

### 커밋 검사
커밋할 때 [pre-commit](https://pre-commit.com)이 스테이징된 파일의 경로에 따라 아래 검사를 실행하고, 실패하면 커밋을 막습니다.

| 경로 | 검사 |
| --- | --- |
| `server` | `ruff check --fix`, `ruff format` |
| `client` | `yarn typecheck:client` |
| `admin` | `yarn typecheck:admin` |
| `yarn.lock`, `.yarnrc.yml` | `client`, `admin` 타입 검사 모두 |

훅은 `yarn install` 때 자동으로 설치되며 [uv](https://docs.astral.sh/uv/)가 필요합니다. ruff가 파일을 수정해 커밋이 중단되면 수정된 파일을 다시 `git add`한 뒤 커밋하세요.

```bash
yarn hooks:install                         # 훅만 따로 설치
uv run --project server pre-commit run -a  # 전체 파일 검사
```

### 공통 의존성
두 개 이상의 워크스페이스가 함께 쓰는 패키지의 버전은 `.yarnrc.yml`의 `catalog`에서 관리하고, 각 `package.json`에는 `"catalog:"`로 표기합니다. 버전을 올릴 때는 `.yarnrc.yml`을 수정한 뒤 `yarn install`을 실행하세요.

## SDK
앱에서는 `@miraepass/api-client`로 가져옵니다.

```ts
import { MiraepassApi, type User } from "@miraepass/api-client";
```

`api-client/src/gen`은 자동 생성되는 폴더입니다. 백엔드 서버(`http://localhost:8000/openapi.json`)를 실행한 뒤 아래 명령어로 다시 생성하세요. 주소가 다르면 `api-client/openapi-ts.config.ts`를 수정합니다.

```bash
yarn sdk-gen
```

## Docker
`client`와 `admin` 이미지는 저장소 루트를 빌드 컨텍스트로 사용합니다. `server`는 기존과 같이 `server` 폴더에서 빌드합니다.

```bash
docker build -f client/Dockerfile .
docker build -f admin/Dockerfile .
docker build server
```

## 릴리스
`client`, `admin`, `server`는 하나의 버전을 함께 사용합니다. `dev`나 `master`에 푸시하면 [semantic-release](https://github.com/semantic-release/semantic-release)가 커밋 메시지로 다음 버전을 정하고, 세 앱의 버전 파일과 루트 `CHANGELOG.md`를 갱신한 뒤 `v1.13.0` 형식의 태그를 만듭니다. `dev`에서는 `v1.13.0-dev.1` 형식의 사전 릴리스가 만들어집니다.

새 버전이 나오면 세 앱의 이미지가 모두 같은 버전으로 빌드됩니다.

```
ghcr.io/scfs-miraepass/mirae-pass/client:<버전>
ghcr.io/scfs-miraepass/mirae-pass/admin:<버전>
ghcr.io/scfs-miraepass/mirae-pass/server:<버전>
```

변경 로그에서 앱을 구분할 수 있도록 커밋에 `feat(client): ...`처럼 scope를 적어 주세요.

### 수동 릴리스
Actions의 `Docker Image Release` 워크플로우를 `manual_version`을 넣어 실행하면 지정한 버전으로 릴리스합니다. 버전 파일, `CHANGELOG.md`, 태그, GitHub Release까지 자동 릴리스와 똑같이 만들어지므로 다음 자동 릴리스는 이 버전 다음부터 이어집니다.

- `master`는 `1.14.0`, `dev`는 `1.14.0-dev.1` 또는 `1.14.0` 형식을 사용합니다.
- 해당 브랜치의 마지막 릴리스보다 높은 버전만 새로 만들 수 있습니다.
- 이미 태그가 있는 버전을 넣으면 릴리스는 만들지 않고 그 태그로 이미지만 다시 빌드합니다.
