"""다나와 HTML 파서.

실제 다나와 페이지 구조가 바뀌면 SELECTORS 상수만 고치면 되도록 분리했다.
"""
import json
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

PRICE_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d{4,}")

# 상품 페이지(prod.danawa.com/info/?pcode=...)의 최저가 후보 선택자 (앞에서부터 시도)
PRODUCT_PRICE_SELECTORS = [
    ".lowest_area .lwst_prc .prc_c",
    ".lowest_price .prc_c",
    ".lwst_prc .prc_c",
    "span.prc_c",
]

# 검색 결과(search.danawa.com/dsearch.php?query=...) 선택자
SEARCH_ITEM_SELECTOR = "li.prod_item"
SEARCH_NAME_SELECTOR = "p.prod_name a, .prod_name a"
SEARCH_PRICE_SELECTORS = [".price_sect a strong", ".price_sect strong", ".prod_pricelist strong"]


@dataclass
class Candidate:
    name: str
    price: int
    url: str = ""


def parse_price(text: str) -> Optional[int]:
    """'1,234,000원' -> 1234000. 숫자가 없으면 None."""
    m = PRICE_RE.search(text or "")
    return int(m.group().replace(",", "")) if m else None


def _json_ld_price(soup: BeautifulSoup) -> Optional[int]:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        for node in data if isinstance(data, list) else [data]:
            offers = node.get("offers") if isinstance(node, dict) else None
            if isinstance(offers, list):
                offers = offers[0] if offers else None
            if isinstance(offers, dict):
                for key in ("lowPrice", "price"):
                    price = parse_price(str(offers.get(key, "")))
                    if price:
                        return price
    return None


def parse_product_page(html: str) -> Optional[Candidate]:
    """상품 페이지에서 (이름, 최저가)를 뽑는다. 실패하면 None."""
    soup = BeautifulSoup(html, "html.parser")

    price = None
    for sel in PRODUCT_PRICE_SELECTORS:
        el = soup.select_one(sel)
        if el and (price := parse_price(el.get_text())):
            break
    if not price:
        price = _json_ld_price(soup)
    if not price:
        meta = soup.find("meta", attrs={"property": "product:price:amount"})
        price = parse_price(meta["content"]) if meta and meta.get("content") else None
    if not price:
        return None

    og = soup.find("meta", attrs={"property": "og:title"})
    title = og["content"] if og and og.get("content") else (soup.title.get_text() if soup.title else "")
    return Candidate(name=title.strip(), price=price)


def parse_search_results(html: str) -> list[Candidate]:
    """검색 결과 목록. 가격이 없는 항목(광고, 품절)은 건너뛴다."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select(SEARCH_ITEM_SELECTOR):
        link = item.select_one(SEARCH_NAME_SELECTOR)
        if not link:
            continue
        price = None
        for sel in SEARCH_PRICE_SELECTORS:
            el = item.select_one(sel)
            if el and (price := parse_price(el.get_text())):
                break
        if price:
            results.append(Candidate(link.get_text(" ", strip=True), price, link.get("href", "")))
    return results


def matches(name: str, include: list[str], exclude: list[str]) -> bool:
    """include는 전부 포함, exclude는 하나라도 있으면 제외 (대소문자 무시)."""
    low = name.lower()
    return all(t.lower() in low for t in include) and not any(t.lower() in low for t in exclude)
