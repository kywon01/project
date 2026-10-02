import sys
from datetime import date, datetime
from pathlib import Path
from time import struct_time
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper  # noqa: E402

TZ = ZoneInfo("Asia/Seoul")


def entry(title, link, utc):
    return {"title": title, "link": link,
            "published_parsed": struct_time(utc + (0, 0, 0))}


class E(dict):
    __getattr__ = dict.__getitem__


def test_filters_yesterday_dedupes_and_interleaves():
    # KST 2026-10-01 = UTC 2026-09-30 15:00 ~ 2026-10-01 14:59
    a = [E(entry("A1", "l1", (2026, 10, 1, 1, 0, 0))),
         E(entry("A2", "l2", (2026, 10, 1, 2, 0, 0))),
         E(entry("OLD", "l3", (2026, 9, 30, 14, 0, 0))),   # KST 9/30 23시 -> 제외
         E(entry("NEW", "l4", (2026, 10, 1, 15, 0, 0)))]   # KST 10/2 00시 -> 제외
    b = [E(entry("a1", "l5", (2026, 10, 1, 3, 0, 0))),     # 제목 중복(대소문자)
         E(entry("B2", "l6", (2026, 10, 1, 4, 0, 0)))]
    got = scraper.select_top([("A", a), ("B", b)], date(2026, 10, 1), TZ, 10)
    assert [g["title"] for g in got] == ["A1", "B2", "A2"]


def test_top_n_limit_and_rows():
    a = [E(entry(f"T{i}", f"l{i}", (2026, 10, 1, 1, i, 0))) for i in range(20)]
    got = scraper.select_top([("A", a)], date(2026, 10, 1), TZ, 10)
    assert len(got) == 10
    rows = scraper.to_rows(got, date(2026, 10, 1), date(2026, 10, 2))
    assert rows[0][:3] == ["2026-10-02", "2026-10-01", 1]
