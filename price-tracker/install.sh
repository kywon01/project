#!/bin/bash
# 가격 수집 자동 실행 설치: venv 생성, 패키지 설치, launchd 예약 등록.
# 사용법: ./install.sh              매일 09:00, 21:00 (기본)
#         ./install.sh 8 13 20      매일 08:00, 13:00, 20:00
#         ./install.sh --uninstall  자동 실행 제거
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.user.price-tracker
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$DEST" 2>/dev/null || true
  rm -f "$DEST"
  echo "자동 실행을 제거했어요."
  exit 0
fi

HOURS=("$@")
[ ${#HOURS[@]} -eq 0 ] && HOURS=(9 21)
for h in "${HOURS[@]}"; do   # 아무것도 건드리기 전에 입력부터 검증한다
  case "$h" in ''|*[!0-9]*) echo "시(hour)는 0~23 사이 숫자여야 해요: $h"; exit 1 ;; esac
  [ "$h" -le 23 ] || { echo "시(hour)는 0~23 사이 숫자여야 해요: $h"; exit 1; }
done

case "$DIR" in
  "$HOME/Documents"*|"$HOME/Desktop"*|"$HOME/Downloads"*)
    echo "경고: 이 폴더($DIR)는 macOS 보호 폴더 안이에요."
    echo "      자동 실행(백그라운드)이 'Operation not permitted'로 막힐 수 있어요."
    echo "      막히면 ~/dev/project 같은 보호 폴더 밖으로 옮긴 뒤 다시 설치하세요."
    ;;
esac

python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"
chmod +x "$DIR/run_all.sh"

mkdir -p "$HOME/Library/LaunchAgents"
TMP="$DEST.tmp"
python3 - "$DIR/$LABEL.plist" "$DIR" "${HOURS[@]}" > "$TMP" <<'PY'
import sys
tpl, d, *hours = sys.argv[1:]
cal = "\n".join(
    f"    <dict><key>Hour</key><integer>{int(h)}</integer><key>Minute</key><integer>0</integer></dict>"
    for h in hours
)
print(open(tpl, encoding="utf-8").read().replace("__DIR__", d).replace("__SCHEDULE__", cal), end="")
PY
if command -v plutil >/dev/null; then plutil -lint "$TMP" >/dev/null || { rm -f "$TMP"; echo "plist 생성 실패"; exit 1; }; fi
mv "$TMP" "$DEST"

launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
launchctl start "$LABEL" || true   # 설치 확인용으로 바로 한 번 실행

echo "설치 완료: 매일 $(printf '%02d:00 ' "${HOURS[@]}")실행 (지금 한 번 실행했어요)"
echo "확인: tail -20 $DIR/run.log"
