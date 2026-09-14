#!/usr/bin/env bash
# 국내 네트워크에서 실행하는 수동 갱신 경로.
# 동행복권이 해외 IP 를 차단하므로, GitHub Actions 가 막힐 때 이 스크립트로 갱신한다.
set -euo pipefail

cd "$(dirname "$0")/.."
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

echo "▶ 소스 접근 확인"
python3 scripts/update_draws.py --probe

echo
echo "▶ 신규 회차 수집"
python3 scripts/update_draws.py "$@"

if git diff --quiet -- docs/data; then
  echo "신규 회차 없음 — 커밋할 내용이 없습니다."
  exit 0
fi

latest=$(python3 -c "import json;print(json.load(open('docs/data/draws.json'))['latestRound'])")
git add docs/data
git commit -m "chore(data): ${latest}회차까지 당첨번호 갱신"
git push -u origin "$BRANCH"
echo "▶ ${latest}회차까지 갱신 후 ${BRANCH} 에 푸시했습니다."
