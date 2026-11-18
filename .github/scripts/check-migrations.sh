#!/bin/sh
# 빈 DB에 마이그레이션을 처음부터 적용해 보고, 모델과 마이그레이션이 맞는지 검사합니다.
#   1. head가 하나인지 (갈라진 마이그레이션이 없는지)
#   2. alembic upgrade head가 성공하는지
#   3. alembic check: 모델을 바꿨는데 마이그레이션을 빠뜨리지 않았는지
# 실패하면 원인과 해결 방법을 작업 요약(GITHUB_STEP_SUMMARY)에 남깁니다.
#
# DATABASE_URL, REDIS_URL, ALLOWED_ORIGINS 환경변수가 필요하며 server 폴더에서 실행합니다.
set -u

summary=${GITHUB_STEP_SUMMARY:-/dev/stdout}
fail() {
  {
    echo "## ❌ 마이그레이션 검사 실패: $1"
    echo
    echo "$2"
  } >> "$summary"
  echo "::error::마이그레이션 검사 실패: $1"
  exit 1
}

prompt() {
  echo
  echo "AI 작업자에게 아래 내용을 그대로 전달해 해결을 요청하세요."
  echo
  echo '```text'
  echo "PR #${PR_NUMBER:-?}의 마이그레이션 검사가 실패했습니다. ($1)"
  echo "아래 로그를 보고 원인을 설명한 뒤, docs/content/docs/development/server.mdx의 마이그레이션 규칙에 맞게 고쳐 주세요."
  echo "기존에 dev에 머지된 마이그레이션 파일은 수정하지 말아 주세요."
  echo
  tail -n 40 "$2"
  echo '```'
}

log=$(mktemp)

heads=$(uv run --locked alembic heads 2> "$log") || fail "head 확인 실패" "$(prompt "alembic heads 실패" "$log")"
head_count=$(echo "$heads" | grep -c . || true)
if [ "$head_count" -gt 1 ]; then
  fail "마이그레이션이 ${head_count}갈래로 갈라졌습니다" "$(cat <<EOF
다른 PR에서 추가한 마이그레이션과 이 PR의 마이그레이션이 같은 지점에서 출발했습니다.

- PR 화면에서 **Update branch** 버튼을 누르면, 자동 수정이 합류 마이그레이션을 추가하고 검사가 다시 실행됩니다.
- 이미 버튼을 눌렀는데도 실패한다면, 이 PR이 같은 저장소의 브랜치에서 올라왔는지 확인하세요. (fork에서 올라온 PR은 자동 수정이 동작하지 않습니다.)

\`\`\`text
$heads
\`\`\`
EOF
)"
fi

if ! uv run --locked alembic upgrade head > "$log" 2>&1; then
  cat "$log"
  fail "빈 DB에 마이그레이션을 적용하지 못했습니다" "$(prompt "alembic upgrade head 실패" "$log")"
fi

if ! uv run --locked alembic check > "$log" 2>&1; then
  cat "$log"
  fail "모델과 마이그레이션이 맞지 않습니다" "$(cat <<EOF
모델(\`app/schemas\`)을 바꿨지만 그에 맞는 마이그레이션이 없습니다.
마이그레이션을 만들어 함께 커밋해야 합니다. ([마이그레이션](https://docs.miraepass.xyz/docs/development/server#마이그레이션) 참고)
$(prompt "alembic check 실패" "$log")
EOF
)"
fi

echo "## ✅ 마이그레이션 검사 통과" >> "$summary"
echo "- head: \`$heads\`" >> "$summary"
