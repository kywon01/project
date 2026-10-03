#!/bin/bash
# 설치/재설치를 한 번에: venv 생성, 패키지 설치, launchd 예약 등록.
# 사용법: ./install.sh [시] [분]     (기본 0 0 = 매일 00:00)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.user.news-scraper
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
HOUR="${1:-0}"
MIN="${2:-0}"

python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

[ -f "$DIR/service_account.json" ] || echo "경고: $DIR/service_account.json 이 없습니다 (Google 키 파일)."

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|/Users/YOUR_NAME/project/news-scraper|$DIR|g" \
    -e "s|<key>Hour</key><integer>0</integer>|<key>Hour</key><integer>$HOUR</integer>|" \
    -e "s|<key>Minute</key><integer>0</integer>|<key>Minute</key><integer>$MIN</integer>|" \
    "$DIR/$LABEL.plist" > "$DEST"

launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
echo "설치 완료: 매일 $(printf '%02d:%02d' "$HOUR" "$MIN") 실행"
