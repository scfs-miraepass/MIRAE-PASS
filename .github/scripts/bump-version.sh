#!/bin/sh
# client, admin, server의 버전 파일을 함께 갱신합니다.
# semantic-release와 수동 릴리스가 모두 이 스크립트를 사용합니다.
set -eu

npm pkg set "version=$1" -w client -w admin
uv --project server version "$1" --no-sync
