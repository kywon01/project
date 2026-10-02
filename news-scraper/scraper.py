"""전날 주요기사 Top N을 RSS로 수집해 Google Sheets에 추가한다.

사용법:
    python scraper.py              # 어제 기사 수집 후 시트에 업로드
    python scraper.py --dry-run    # 업로드 없이 결과만 출력
    python scraper.py --date 2026-10-01
"""
import argparse
import json
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

BASE_DIR = Path(__file__).resolve().parent
HEADER = ["수집일", "기사일", "순위", "제목", "출처", "링크", "발행시각"]
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


def select_top(feeds_entries, target, tz, top_n):
    """피드별 순서를 유지한 채 번갈아 뽑아 target 날짜 기사 top_n개를 고른다.

    RSS에는 조회수 같은 인기 지표가 없어서, 각 피드가 제공하는 노출 순서(주요기사 순)를
    기준으로 하고 매체가 한쪽으로 쏠리지 않게 라운드로빈으로 섞는다.
    """
    queues = []
    for name, entries in feeds_entries:
        items = []
        for e in entries:
            d, dt = published_date(e, tz)
            if d != target or not e.get("title") or not e.get("link"):
                continue
            items.append({"title": e.title.strip(), "link": e.link,
                          "source": name, "published": dt})
        queues.append(items)

    picked, seen_titles, seen_links = [], set(), set()
    while len(picked) < top_n and any(queues):
        for q in queues:
            while q:
                item = q.pop(0)
                key = item["title"].lower()
                if key in seen_titles or item["link"] in seen_links:
                    continue
                seen_titles.add(key)
                seen_links.add(item["link"])
                picked.append(item)
                break
            if len(picked) >= top_n:
                break
    return picked


def to_rows(items, target, today):
    return [[today.isoformat(), target.isoformat(), i, it["title"], it["source"],
             it["link"], it["published"].strftime("%Y-%m-%d %H:%M")]
            for i, it in enumerate(items, 1)]


def upload(rows, target, cfg):
    import gspread

    sa_path = Path(cfg["service_account_file"])
    if not sa_path.is_absolute():
        sa_path = BASE_DIR / sa_path
    gc = gspread.service_account(filename=str(sa_path))
    sh = gc.open_by_key(cfg["spreadsheet_id"])
    try:
        ws = sh.worksheet(cfg["worksheet"])
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(cfg["worksheet"], rows=1000, cols=len(HEADER))
    if ws.row_values(1) != HEADER:
        ws.insert_row(HEADER, 1)
    # 같은 기사일이 이미 있으면 중복 추가하지 않는다 (재실행 안전).
    if target.isoformat() in ws.col_values(2)[1:]:
        log.info("%s 데이터가 이미 있어 건너뜀", target)
        return False
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return True


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

    feeds_entries = [(f["name"], fetch_feed(f)) for f in cfg["feeds"]]
    items = select_top(feeds_entries, target, tz, cfg["top_n"])
    if not items:
        log.error("%s 기사를 한 건도 찾지 못함 (네트워크/피드 확인)", target)
        return 1
    rows = to_rows(items, target, today)
    for r in rows:
        print(" | ".join(str(c) for c in r[2:5]))
    if len(rows) < cfg["top_n"]:
        log.warning("목표 %d건 중 %d건만 수집", cfg["top_n"], len(rows))
    if args.dry_run:
        return 0
    if not cfg.get("spreadsheet_id"):
        log.error("config.json에 spreadsheet_id가 비어 있음")
        return 1
    if upload(rows, target, cfg):
        log.info("%d건 업로드 완료", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
