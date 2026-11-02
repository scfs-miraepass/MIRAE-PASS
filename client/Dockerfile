# 빌드 환경 (Builder)
FROM node:24-slim AS builder

WORKDIR /src

COPY package.json yarn.lock ./

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/* \
    && yarn install

COPY . .
RUN yarn postinstall && yarn build

# 실행 환경 (Runner)
FROM node:24-slim

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /src/.output ./.output

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

ENV PORT=3000
ENV HOST=0.0.0.0
EXPOSE 3000

# DB 생성 및 실행
CMD ["node", ".output/server/index.mjs"]
