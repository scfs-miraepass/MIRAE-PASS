"""서버를 실행하지 않고 FastAPI 앱의 OpenAPI 문서를 파일로 저장합니다.

CI에서 SDK를 다시 만들 때 사용합니다. 앱을 import하기만 하므로 DB·Redis에 접속하지 않지만,
설정 검증을 통과하도록 DATABASE_URL, REDIS_URL, ALLOWED_ORIGINS 환경변수에 가짜 값을 넣어 실행합니다.

사용법: uv run --project server python .github/scripts/dump-openapi.py <출력 경로>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "server"))

from app.main import app

# 로컬에서 http://localhost:8000/openapi.json으로 만든 SDK와 결과가 같도록 기본 주소를 넣습니다.
schema = app.openapi()
schema.setdefault("servers", [{"url": "http://localhost:8000"}])

Path(sys.argv[1]).write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OpenAPI] {len(schema['paths'])}개 경로를 {sys.argv[1]}에 저장했습니다.")
