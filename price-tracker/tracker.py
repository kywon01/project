#!/usr/bin/env python3
"""다나와 최저가 추적기.

    python3 tracker.py run              # 전체 상품 가격 수집 + 알림
    python3 tracker.py run --save-html html/   # 받은 HTML 저장 (파서 디버깅용)
    python3 tracker.py history          # 저장된 가격 이력 보기
"""
import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

import requests

import db
from parsers import Candidate, matches, parse_product_page, parse_search_results

HERE = Path(__file__).parent
SEARCH_URL = "https://search.danawa.com/dsearch.php?query={q}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
REQUEST_DELAY_SEC = 3  # 서버에 부담 주지 않도록 상품 사이에 쉰다
MIN_PRICE_RATIO = 0.5  # 공식가의 이 비율 미만은 액세서리/오등록으로 보고 제외한다


@dataclass
class Product:
    name: str
    query: str
    url: str
    official_price: int
    target_price: int
    include: list[str]
    exclude: list[str]


def load_products(path: Path) -> list[Product]:
    def split(s: str) -> list[str]:
        return [t.strip() for t in s.split("|") if t.strip()]

    with open(path, encoding="utf-8", newline="") as f:
        return [
            Product(
                name=r["name"],
                query=r["query"],
                url=r["url"].strip(),
                official_price=int(r["official_price"] or 0),
                target_price=int(r["target_price"] or 0),
                include=split(r["must_include"]),
                exclude=split(r["must_exclude"]),
            )
            for r in csv.DictReader(f)
        ]


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def find_price(
    p: Product, get: Callable[[str], str], save_dir: Optional[Path] = None, verbose: bool = False
) -> Optional[Candidate]:
    """url이 있으면 상품 페이지에서, 없으면 검색 결과에서 조건에 맞는 최저가를 찾는다."""
    if p.url:
        html = get(p.url)
        _maybe_save(save_dir, p.name, "product", html)
        cand = parse_product_page(html)
        if cand:
            cand.url = p.url
        return cand

    html = get(SEARCH_URL.format(q=quote(p.query)))
    _maybe_save(save_dir, p.name, "search", html)
    results = parse_search_results(html)
    by_name = [c for c in results if matches(c.name, p.include, p.exclude)]
    floor = p.official_price * MIN_PRICE_RATIO
    ok = [c for c in by_name if c.price >= floor]
    print(f"   검색 결과 {len(results)}건 중 조건에 맞는 것 {len(ok)}건")
    if len(by_name) > len(ok):
        print(f"   (공식가의 {MIN_PRICE_RATIO:.0%} 미만이라 제외한 것 {len(by_name) - len(ok)}건 - 액세서리일 수 있어요)")
    if verbose:
        for c in sorted(results, key=lambda c: c.price):
            mark = "✓" if c in ok else "!" if c in by_name else "·"
            print(f"     {mark} {c.price:>9,}원  {c.name}")
    if not ok:
        print(f"   조건에 맞는 검색 결과가 없어요. 상위 후보 {min(5, len(results))}개:")
        for c in results[:5]:
            print(f"     - {c.price:>9,}원  {c.name}")
        if not results:
            print("     (검색 결과 0건 - 파서 선택자가 맞는지 --save-html로 확인해 보세요)")
        return None
    return min(ok, key=lambda c: c.price)


def _maybe_save(save_dir: Optional[Path], name: str, kind: str, html: str) -> None:
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in name)
        (save_dir / f"{safe}.{kind}.html").write_text(html, encoding="utf-8")


def alerts(p: Product, price: int, prev: Optional[int], lowest: Optional[int]) -> list[str]:
    msgs = []
    if p.target_price and price <= p.target_price:
        msgs.append(f"목표가 {p.target_price:,}원 이하 도달!")
    if p.official_price and price < p.official_price:
        diff = p.official_price - price
        msgs.append(f"애플 공식가보다 {diff:,}원({diff / p.official_price:.0%}) 저렴")
    if prev is not None and price < prev:
        msgs.append(f"직전 수집가({prev:,}원)보다 {prev - price:,}원 하락")
    if lowest is not None and price < lowest:
        msgs.append("역대 최저가 갱신!")
    return msgs


def run(
    products: list[Product], conn, get=fetch, save_dir: Optional[Path] = None,
    delay: float = REQUEST_DELAY_SEC, verbose: bool = False,
) -> int:
    failures = 0
    for i, p in enumerate(products):
        if i:
            time.sleep(delay)
        print(f"\n[{p.name}]  공식가 {p.official_price:,}원 / 목표가 {p.target_price:,}원")
        try:
            cand = find_price(p, get, save_dir, verbose)
        except requests.RequestException as e:
            print(f"   접속 실패: {e}")
            failures += 1
            continue
        if not cand:
            failures += 1
            continue

        prev, lowest = db.last_price(conn, p.name), db.lowest_price(conn, p.name)
        db.save_price(conn, p.name, cand.price, cand.name, cand.url)
        print(f"   현재 최저가 {cand.price:,}원  ({cand.name})")
        for m in alerts(p, cand.price, prev, lowest):
            print(f"   ★ {m}")
    return failures


def show_history(products: list[Product], conn) -> None:
    for p in products:
        rows = db.history(conn, p.name)
        print(f"\n[{p.name}]")
        if not rows:
            print("   기록 없음")
        for at, price, matched in rows:
            print(f"   {at}  {price:>9,}원  {matched}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "history"])
    ap.add_argument("--products", type=Path, default=HERE / "products.csv")
    ap.add_argument("--db", default=str(HERE / "prices.db"))
    ap.add_argument("--save-html", type=Path, help="받은 HTML을 이 폴더에 저장")
    ap.add_argument("--verbose", action="store_true", help="검색 결과 전체와 매칭 여부를 보여줌 (✓=후보, !=너무 싸서 제외, ·=이름 불일치)")
    args = ap.parse_args(argv)

    products = load_products(args.products)
    conn = db.connect(args.db)
    if args.command == "history":
        show_history(products, conn)
        return 0
    return 1 if run(products, conn, save_dir=args.save_html, verbose=args.verbose) else 0


if __name__ == "__main__":
    sys.exit(main())
