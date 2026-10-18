#!/bin/bash
# 자동 실행이 호출하는 스크립트: 가격 수집 -> 대시보드 갱신. 직접 실행해도 된다: ./run_all.sh
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
.venv/bin/python tracker.py run
status=$?
.venv/bin/python dashboard.py
exit $status
