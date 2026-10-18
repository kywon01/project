"""전날 주요기사 Top N을 RSS로 수집해 Google Sheets에 추가한다.

사용법:
    python scraper.py              # 어제 기사 수집 후 시트에 업로드
    python scraper.py --dry-run    # 업로드 없이 결과만 출력
    python scraper.py --date 2026-10-01
"""
import argparse
import json
import logging
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

BASE_DIR = Path(__file__).resolve().parent
HEADER = ["수집일", "기사일", "순위", "제목", "출처", "링크", "발행시각"]
LOG_HEADER = ["실행시각", "기사일", "상태", "메시지"]
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
MISSING_DAYS_WINDOW = 7
log = logging.getLogger("news-scraper")


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_feed(feed, retries=3):
    """피드 하나를 받아온다. 실패하면 재시도하고, 끝까지 실패하면 빈 목록."""
    for attempt in range(1, retries + 1):
        parsed = feedparser.parse(feed["url"], agent="Mozilla/5.0 news-scraper")
        if parsed.entries:
            return parsed.entries
        log.warning("%s: 항목 없음 (시도 %d/%d)", feed["name"], attempt, retries)
        time.sleep(2 * attempt)
    return []


def published_date(entry, tz):
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    if not ts:
        return None, None
    dt = datetime(*ts[:6], tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return dt.date(), dt


def compile_keywords(words):
    """제목에서 IT 기사를 찾을 키워드 정규식. 영문 키워드는 단어 경계를 지킨다."""
    parts = []
    for w in words or []:
        if re.fullmatch(r"[A-Za-z0-9 .+#-]+", w):
            parts.append(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])")
        else:
            parts.append(re.escape(w))
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


def title_tokens(title):
    return {t.lower() for t in TOKEN_RE.findall(title)}


def is_similar(a, b, min_common=4, ratio=0.6):
    """제목 단어가 min_common개 이상 겹치고 짧은 쪽의 ratio 이상이면 같은 주제로 본다."""
    inter = len(a & b)
    return bool(a and b) and inter >= min_common and inter / min(len(a), len(b)) >= ratio


class _Picker:
    def __init__(self, top_n, min_common, ratio):
        self.top_n, self.min_common, self.ratio = top_n, min_common, ratio
        self.picked, self.titles, self.links, self.tokens = [], set(), set(), []

    def accept(self, item):
        key = item["title"].lower()
        if key in self.titles or item["link"] in self.links:
            return False
        toks = title_tokens(item["title"])
        if any(is_similar(toks, t, self.min_common, self.ratio) for t in self.tokens):
            return False
        self.titles.add(key)
        self.links.add(item["link"])
        self.tokens.append(toks)
        self.picked.append(item)
        return True

    def fill(self, queues):
        """각 큐에서 번갈아 하나씩 뽑는다 (매체 쏠림 방지)."""
        while len(self.picked) < self.top_n and any(queues):
            for q in queues:
                while q:
                    if self.accept(q.pop(0)):
                        break
                if len(self.picked) >= self.top_n:
                    break


def select_top(feeds_entries, target, tz, top_n, keyword_re=None, strict=False,
               min_common=4, ratio=0.6):
    """target 날짜 기사 top_n개를 고른다.

    RSS에는 조회수 같은 인기 지표가 없어서, 각 피드가 제공하는 노출 순서(주요기사 순)를
    기준으로 하고 매체가 한쪽으로 쏠리지 않게 라운드로빈으로 섞는다.
    keyword_re가 있으면 제목에 키워드가 든 기사를 먼저 채우고, 모자랄 때만(strict가
    아니면) 나머지로 채운다. 같은 주제로 보이는 제목은 하나만 남긴다.
    """
    matched_qs, other_qs = [], []
    for name, entries in feeds_entries:
        matched, other = [], []
        for e in entries:
            d, dt = published_date(e, tz)
            title = (e.get("title") or "").strip()
            if d != target or not title or not e.get("link"):
                continue
            item = {"title": title, "link": e.get("link"), "source": name, "published": dt}
            if keyword_re is None or keyword_re.search(title):
                matched.append(item)
            else:
                other.append(item)
        matched_qs.append(matched)
        other_qs.append(other)

    picker = _Picker(top_n, min_common, ratio)
    picker.fill(matched_qs)
    if not strict:
        picker.fill(other_qs)
    return picker.picked


def to_rows(items, target, today):
    return [[today.isoformat(), target.isoformat(), i, it["title"], it["source"],
             it["link"], it["published"].strftime("%Y-%m-%d %H:%M")]
            for i, it in enumerate(items, 1)]


def missing_days(dates, target, window=MISSING_DAYS_WINDOW):
    """시트에 이미 있는 기사일(dates) 중 최근 window일 안에서 빠진 날짜를 돌려준다.

    시트에 처음 데이터가 생긴 날 이전은 검사하지 않는다.
    """
    if not dates:
        return []
    day = max(min(dates), target - timedelta(days=window - 1))
    missing = []
    while day <= target:
        if day not in dates:
            missing.append(day)
        day += timedelta(days=1)
    return missing


def open_spreadsheet(cfg):
    import gspread

    sa_path = Path(cfg["service_account_file"])
    if not sa_path.is_absolute():
        sa_path = BASE_DIR / sa_path
    gc = gspread.service_account(filename=str(sa_path))
    return gc.open_by_key(cfg["spreadsheet_id"])


def get_worksheet(sh, name, header):
    import gspread

    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(name, rows=1000, cols=len(header))
    if ws.row_values(1) != header:
        ws.insert_row(header, 1)
    return ws


def upload(ws, rows, target):
    """같은 기사일이 이미 있으면 추가하지 않는다 (재실행 안전). 추가했으면 True."""
    if target.isoformat() in ws.col_values(2)[1:]:
        log.info("%s 데이터가 이미 있어 건너뜀", target)
        return False
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return True


def sheet_dates(ws):
    return {date.fromisoformat(v) for v in ws.col_values(2)[1:]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)}


def notify(cfg, message):
    """맥 알림 센터로 알린다 (설정 notify.macos 가 true일 때, macOS에서만)."""
    if not cfg.get("notify", {}).get("macos") or sys.platform != "darwin":
        return
    text = json.dumps(message.replace("\n", " "), ensure_ascii=False)
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification {text} with title "news-scraper"'],
                       check=False, timeout=10)
    except Exception:  # 알림 실패가 본 작업을 막으면 안 된다
        log.warning("알림 전송 실패", exc_info=True)


def record(cfg, tz, target, status, message, sh=None):
    """Log 탭에 실행 결과 한 줄을 남긴다. 실패해도 예외를 내지 않는다."""
    name = cfg.get("log_worksheet")
    if not name or not cfg.get("spreadsheet_id"):
        return
    try:
        sh = sh or open_spreadsheet(cfg)
        ws = get_worksheet(sh, name, LOG_HEADER)
        ws.append_row([datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"), target.isoformat(),
                       status, message], value_input_option="USER_ENTERED")
    except Exception:
        log.warning("Log 탭 기록 실패", exc_info=True)


def run(args, cfg, tz, today, target):
    feeds_entries = [(f["name"], fetch_feed(f)) for f in cfg["feeds"]]
    items = select_top(
        feeds_entries, target, tz, cfg["top_n"],
        keyword_re=compile_keywords(cfg.get("keywords")),
        strict=cfg.get("strict_keywords", False),
        min_common=cfg.get("similar_min_common", 4),
        ratio=cfg.get("similar_ratio", 0.6),
    )
    if not items:
        raise RuntimeError(f"{target} 기사를 한 건도 찾지 못함 (네트워크/피드 확인)")
    rows = to_rows(items, target, today)
    for r in rows:
        print(" | ".join(str(c) for c in r[2:5]))

    notes = []
    if len(rows) < cfg["top_n"]:
        notes.append(f"목표 {cfg['top_n']}건 중 {len(rows)}건만 수집")
        log.warning(notes[-1])
    if args.dry_run:
        return 0
    if not cfg.get("spreadsheet_id"):
        raise RuntimeError("config.json에 spreadsheet_id가 비어 있음")

    sh = open_spreadsheet(cfg)
    ws = get_worksheet(sh, cfg["worksheet"], HEADER)
    if upload(ws, rows, target):
        log.info("%d건 업로드 완료", len(rows))
        status, msg = "OK", f"{len(rows)}건 업로드"
    else:
        status, msg = "OK", "이미 있어 건너뜀"

    gaps = missing_days(sheet_dates(ws), target)
    if gaps:
        gap_msg = "빠진 기사일: " + ", ".join(d.isoformat() for d in gaps)
        log.warning(gap_msg)
        notes.append(gap_msg)
        notify(cfg, f"news-scraper 경고: {gap_msg}")
    if notes:
        status, msg = "WARN", msg + " / " + " / ".join(notes)
    record(cfg, tz, target, status, msg, sh)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(BASE_DIR / "config.json"))
    ap.add_argument("--date", help="수집할 기사일 (YYYY-MM-DD). 기본: 어제")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    cfg = load_config(args.config)
    tz = ZoneInfo(cfg["timezone"])
    today = datetime.now(tz).date()
    target = date.fromisoformat(args.date) if args.date else today - timedelta(days=1)

    try:
        return run(args, cfg, tz, today, target)
    except Exception as e:
        log.exception("실패")
        if not args.dry_run:
            message = f"{type(e).__name__}: {e}"
            notify(cfg, f"news-scraper 실패 ({target}): {message}")
            record(cfg, tz, target, "ERROR", message)
        return 1


if __name__ == "__main__":
    sys.exit(main())
