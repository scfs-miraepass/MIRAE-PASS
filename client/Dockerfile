# 빌드 컨텍스트는 저장소 루트입니다: docker build -f client/Dockerfile .
# 빌드 환경 (Builder)
FROM node:24-slim AS builder

WORKDIR /src

COPY package.json yarn.lock .yarnrc.yml ./
COPY client/package.json client/
COPY admin/package.json admin/
COPY api-client/package.json api-client/

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && yarn install --immutable

COPY . .
RUN yarn workspace scfs-miraepass-front postinstall && yarn workspace scfs-miraepass-front build

# 실행 환경 (Runner)
FROM node:24-slim

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /src/client/.output ./.output

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

ENV PORT=3000
ENV HOST=0.0.0.0
EXPOSE 3000

# DB 생성 및 실행
CMD ["node", ".output/server/index.mjs"]
