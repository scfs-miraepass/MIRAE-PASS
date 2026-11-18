#!/bin/sh
# master의 변경 사항(정식 릴리스 커밋 등)을 dev에 반영합니다.
# - dev에 새 커밋이 없고 master 마지막 커밋에 [skip ci]가 있으면 dev를 master로 fast-forward합니다.
# - 그 밖의 경우 [skip ci]가 붙은 merge 커밋을 만들어, dev push로 프리릴리스가 만들어지지 않게 합니다.
# - 충돌이 나면 아무것도 push하지 않고 이슈를 만들어 알립니다.
set -eu

git fetch origin master dev

if git merge-base --is-ancestor origin/master origin/dev; then
  echo "[dev 동기화] dev에 master의 변경 사항이 이미 반영되어 있습니다."
  exit 0
fi

master_subject=$(git log -1 --format=%s origin/master)
case "$master_subject" in
  *"[skip ci]"*) master_skip_ci=true ;;
  *) master_skip_ci=false ;;
esac

if git merge-base --is-ancestor origin/dev origin/master && [ "$master_skip_ci" = true ]; then
  git push origin origin/master:refs/heads/dev
  echo "[dev 동기화] dev를 master로 fast-forward했습니다: $master_subject"
  exit 0
fi

git checkout -B dev origin/dev
if git merge --no-ff origin/master -m "chore: master 변경 사항을 dev에 반영 [skip ci]"; then
  git push origin HEAD:refs/heads/dev
  echo "[dev 동기화] master를 dev에 merge했습니다."
  exit 0
fi

conflicts=$(git diff --name-only --diff-filter=U)
git merge --abort

title="[자동] master를 dev에 반영하지 못했습니다"
if [ -z "$(gh issue list --state open --search "\"$title\" in:title" --json number --jq '.[].number')" ]; then
  body_file=$(mktemp)
  {
    echo "master의 변경 사항을 dev에 합치다가 충돌이 발생했습니다. dev 브랜치는 바뀌지 않았습니다."
    echo
    echo "### 충돌한 파일"
    echo "$conflicts" | sed 's/^/- `/; s/$/`/'
    echo
    echo "### 해결 방법"
    echo "[배포 문서의 dev 동기화](https://docs.miraepass.xyz/docs/development/deploy#dev-동기화)를 참고하세요."
    echo "충돌을 해결해 dev에 반영한 뒤 이 이슈를 닫습니다."
  } > "$body_file"
  gh issue create --title "$title" --body-file "$body_file"
fi

echo "[dev 동기화] 충돌이 발생해 이슈를 만들었습니다." >&2
exit 1
