#!/bin/sh
# PR 브랜치에서 사람이 하지 않아도 되는 정리 작업을 자동으로 커밋합니다.
#   1. 마이그레이션 head가 여러 개면 alembic merge heads로 합류 마이그레이션을 추가합니다.
#      기존 마이그레이션 파일은 수정하지 않습니다.
#   2. 서버 API에 맞춰 SDK(api-client/src/gen)를 다시 만들고, 바뀌었으면 커밋합니다.
# 커밋이 생기면 PR 브랜치에 push하고 GITHUB_OUTPUT에 pushed=true를 남깁니다.
#
# 필요한 환경변수: BASE_REF(PR 대상 브랜치), HEAD_REF(PR 브랜치)
set -eu

root=$(pwd)
pushed=false
set_output() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "pushed=$1" >> "$GITHUB_OUTPUT"; fi
}

# 같은 정리가 반복되면(생성 결과가 매번 달라지는 경우 등) 무한히 커밋하지 않도록 멈춥니다.
last_subject=$(git log -1 --format=%s)
guard() {
  case "$last_subject" in
    "$1"*)
      echo "::error::직전 자동 커밋('$last_subject') 뒤에도 같은 정리가 다시 필요합니다. 자동 수정을 멈춥니다."
      exit 1
      ;;
  esac
}

alembic() { (cd "$root/server" && uv run --locked alembic "$@"); }

# 1. 마이그레이션 합류
heads=$(alembic heads | awk '{print $1}')
head_count=$(echo "$heads" | grep -c . || true)
if [ "$head_count" -gt 1 ]; then
  guard "chore(server): 마이그레이션 합류"

  # 이름은 이 PR에서 추가한 마이그레이션의 버전을 따릅니다. (예: v1.16.0 → v1.16.0_merge)
  git fetch --quiet origin "$BASE_REF"
  name=""
  for rev in $heads; do
    file=$(ls "server/alembic/versions/${rev}_"*.py 2>/dev/null | head -n 1)
    [ -n "$file" ] || continue
    if ! git cat-file -e "origin/$BASE_REF:$file" 2>/dev/null; then
      # 파일 이름은 alembic이 '.'을 '_'로 바꾸므로, 파일 첫 줄의 메시지("""v1.16.0)에서 읽습니다.
      name=$(sed -n '1s/^"""//p' "$file" | sed -E 's/_merge$//; s/_[0-9]+$//')
      break
    fi
  done
  message="${name:+${name}_}merge"

  alembic merge heads -m "$message"
  new_file=$(git ls-files --others --exclude-standard server/alembic/versions)
  (cd server && uv run --locked ruff check --fix --quiet $(echo "$new_file" | sed 's#^server/##') \
    && uv run --locked ruff format --line-length=120 --quiet $(echo "$new_file" | sed 's#^server/##'))

  git add server/alembic/versions
  git commit --quiet -m "chore(server): 마이그레이션 합류 ($(echo $heads | tr ' ' ','))"
  echo "[자동 수정] 갈라진 마이그레이션 ${head_count}개를 합류했습니다: $new_file"
fi

# 2. SDK 다시 만들기
openapi=$(mktemp -d)/openapi.json
DATABASE_URL="mysql+aiomysql://ci:ci@127.0.0.1:3306/ci" REDIS_URL="redis://127.0.0.1:6379" ALLOWED_ORIGINS="*" \
  uv run --locked --project server python -I .github/scripts/dump-openapi.py "$openapi"
OPENAPI_INPUT="$openapi" yarn sdk-gen > /dev/null

if [ -n "$(git status --porcelain -- api-client/src/gen)" ]; then
  guard "chore(sdk): SDK 재생성"
  git add api-client/src/gen
  git commit --quiet -m "chore(sdk): SDK 재생성 (기준 $(git rev-parse --short HEAD))"
  echo "[자동 수정] SDK를 다시 만들었습니다."
fi

# 커밋이 생겼으면 PR 브랜치에 push합니다.
if [ -n "$(git log --format=%H "origin/$HEAD_REF..HEAD")" ]; then
  git push --quiet origin "HEAD:refs/heads/$HEAD_REF"
  pushed=true
  echo "[자동 수정] PR 브랜치에 자동 수정 커밋을 올렸습니다. 검사가 다시 실행됩니다."
else
  echo "[자동 수정] 고칠 것이 없습니다."
fi
set_output "$pushed"
