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
`client`, `admin`, `api-client`는 Yarn(v1) 워크스페이스입니다. 의존성은 저장소 루트에서 설치하며 `yarn.lock`도 루트에 하나만 둡니다.
`server`는 워크스페이스에 포함되지 않고 `uv`로 따로 관리합니다. [server/README.md](server/README.md)를 참고하세요.

```bash
yarn install

yarn dev:client         # 또는 dev:admin
yarn build:client       # 또는 build:admin
yarn typecheck:client   # 또는 typecheck:admin
```

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
