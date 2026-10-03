#!/bin/bash
# 현재 상태를 한 번에 확인한다: ./status.sh
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.user.news-scraper.plist"

echo "== 현재 시각 =="; date
echo; echo "== 예약 등록 =="
launchctl list | grep news-scraper || echo "등록 안 됨 (./install.sh 실행 필요)"
echo; echo "== 예약 시각 =="
grep -A3 StartCalendar "$PLIST" 2>/dev/null | grep integer | sed 's/<[^>]*>//g' || echo "plist 없음"
echo; echo "== 마지막 실행 로그 =="
grep -E "INFO|WARNING|ERROR" "$DIR/scraper.log" 2>/dev/null | tail -5 || echo "로그 없음"
echo; echo "== 잠자기 설정 =="
pmset -g | grep -E "^ *(sleep|displaysleep)"
echo; echo "== FileVault =="; fdesetup status
