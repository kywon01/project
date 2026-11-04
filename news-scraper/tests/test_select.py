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


def day(titles, links=None):
    return [E(entry(t, f"l-{t}", (2026, 10, 1, 1, i, 0))) for i, t in enumerate(titles)]


def test_keyword_items_come_first_and_fill_when_short():
    kw = scraper.compile_keywords(["AI", "반도체"])
    a = day(["단풍 구경 언제 갈까", "AI 에이전트 공개", "시승기 투아렉", "반도체 공장 입지"])
    got = scraper.select_top([("A", a)], date(2026, 10, 1), TZ, 3, keyword_re=kw)
    assert [g["title"] for g in got] == ["AI 에이전트 공개", "반도체 공장 입지", "단풍 구경 언제 갈까"]


def test_strict_keywords_does_not_fill():
    kw = scraper.compile_keywords(["AI"])
    a = day(["단풍 구경", "AI 에이전트"])
    got = scraper.select_top([("A", a)], date(2026, 10, 1), TZ, 5, keyword_re=kw, strict=True)
    assert [g["title"] for g in got] == ["AI 에이전트"]


def test_ascii_keyword_respects_word_boundary():
    kw = scraper.compile_keywords(["AI", "IT"])
    assert kw.search("베슬AI, GPU 확보")
    assert kw.search("[IT애정남] 충전 케이블")
    assert not kw.search("MAIN 시승기 FIT")


def test_similar_titles_are_deduped():
    a = day(["베슬AI, 2030년 GPU 20만 장 확보 추진…‘글로벌 네오클라우드’ 도약",
             "인스웨이브, 89억 규모 새마을금고 웹단말 전환 수주"])
    b = day(["베슬AI, '베슬 클라우드' 청사진 소개··· \"2030년 GPU 20만 장 확보 목표\""])
    got = scraper.select_top([("A", a), ("B", b)], date(2026, 10, 1), TZ, 10)
    assert len(got) == 2 and got[0]["source"] == "A" and got[1]["source"] == "A"


def test_different_topics_are_not_merged():
    a = day(["엔비디아 ‘RTX 스파크’, 한국 상륙…1호 구매자는 래블업 대표"])
    b = day(["“AI 구독료 잡는다”…엔비디아, ‘RTX 스파크’로 로컬 AI 시장 공략"])
    got = scraper.select_top([("A", a), ("B", b)], date(2026, 10, 1), TZ, 10)
    assert len(got) == 2


def test_missing_days_detects_gap_after_first_data():
    have = {date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 4)}
    assert scraper.missing_days(have, date(2026, 10, 4)) == [date(2026, 10, 3)]
    assert scraper.missing_days(set(), date(2026, 10, 4)) == []
    assert scraper.missing_days({date(2026, 10, 4)}, date(2026, 10, 4)) == []
