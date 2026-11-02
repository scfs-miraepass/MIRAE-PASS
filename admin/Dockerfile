# 빌드 컨텍스트는 저장소 루트입니다: docker build -f admin/Dockerfile .
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
RUN yarn workspace scfs-miraepass-dashboard postinstall && yarn workspace scfs-miraepass-dashboard build

# 실행 환경 (Runner)
FROM node:24-slim

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /src/admin/.output ./.output

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

ENV PORT=5234
ENV HOST=0.0.0.0
EXPOSE 5234

# DB 생성 및 실행
CMD ["node", ".output/server/index.mjs"]
