"""파서/알림 로직 테스트. 아래 HTML은 다나와 구조를 가정해 직접 만든 샘플이다(실제 페이지 아님)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import tracker
from parsers import matches, parse_price, parse_product_page, parse_search_results

SEARCH_HTML = """
<ul>
  <li class="prod_item"><p class="prod_name"><a href="/a">APPLE 매직 마우스 USB-C 블랙</a></p>
      <p class="price_sect"><a><strong>105,000</strong></a></p></li>
  <li class="prod_item"><p class="prod_name"><a href="/b">APPLE 매직 마우스 USB-C 화이트 (MXK53KH/A)</a></p>
      <p class="price_sect"><a><strong>89,900</strong></a></p></li>
  <li class="prod_item"><p class="prod_name"><a href="/c">APPLE 매직 마우스 USB-C 화이트 (병행)</a></p>
      <p class="price_sect"><a><strong>92,000</strong></a></p></li>
  <li class="prod_item"><p class="prod_name"><a href="/d">가격없는 광고</a></p></li>
</ul>"""

PRODUCT_HTML = """
<html><head><meta property="og:title" content="APPLE 매직 키보드 Touch ID"></head>
<body><div class="lowest_area"><div class="lwst_prc"><span class="prc_c">187,000</span>원</div></div></body></html>"""

JSON_LD_HTML = """
<html><head><script type="application/ld+json">
{"@type":"Product","name":"X","offers":{"@type":"AggregateOffer","lowPrice":"123000"}}
</script></head><body></body></html>"""


class ParserTests(unittest.TestCase):
    def test_parse_price(self):
        self.assertEqual(parse_price("1,234,000원"), 1234000)
        self.assertEqual(parse_price("99000"), 99000)
        self.assertIsNone(parse_price("가격 비교중"))

    def test_search_skips_items_without_price(self):
        self.assertEqual(len(parse_search_results(SEARCH_HTML)), 3)

    def test_product_page_selector_and_title(self):
        c = parse_product_page(PRODUCT_HTML)
        self.assertEqual((c.price, c.name), (187000, "APPLE 매직 키보드 Touch ID"))

    def test_product_page_json_ld_fallback(self):
        self.assertEqual(parse_product_page(JSON_LD_HTML).price, 123000)

    def test_product_page_no_price(self):
        self.assertIsNone(parse_product_page("<html></html>"))

    def test_matches(self):
        self.assertTrue(matches("애플 매직 마우스 USB-C 화이트", ["마우스", "usb-c"], ["블랙"]))
        self.assertFalse(matches("애플 매직 마우스 USB-C 블랙", ["마우스"], ["블랙"]))
        self.assertFalse(matches("애플 매직 트랙패드", ["마우스"], []))


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.connect(str(Path(self.tmp.name) / "t.db"))
        self.mouse = tracker.Product("마우스", "q", "", 99000, 88000, ["마우스", "USB-C"], ["블랙"])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_search_picks_cheapest_matching_not_cheapest_overall(self):
        cand = tracker.find_price(self.mouse, lambda url: SEARCH_HTML)
        self.assertEqual(cand.price, 89900)  # 블랙(105,000)과 광고는 제외, 화이트 중 최저가

    def test_url_mode_uses_product_page(self):
        p = tracker.Product("키보드", "", "https://example/p", 199000, 175000, [], [])
        self.assertEqual(tracker.find_price(p, lambda url: PRODUCT_HTML).price, 187000)

    def test_alerts(self):
        msgs = tracker.alerts(self.mouse, 85000, prev=89900, lowest=89900)
        self.assertEqual(len(msgs), 4)
        self.assertEqual(tracker.alerts(self.mouse, 99000, prev=99000, lowest=95000), [])

    def test_run_saves_history_and_detects_drop(self):
        out = []
        for price_html in (SEARCH_HTML, SEARCH_HTML.replace("89,900", "80,000")):
            tracker.run([self.mouse], self.conn, get=lambda url, h=price_html: h, delay=0)
        self.assertEqual([r[1] for r in db.history(self.conn, "마우스")], [80000, 89900])
        self.assertEqual(db.lowest_price(self.conn, "마우스"), 80000)

    def test_run_counts_failure_when_nothing_matches(self):
        p = tracker.Product("없는상품", "q", "", 1, 1, ["존재하지않음"], [])
        self.assertEqual(tracker.run([p], self.conn, get=lambda url: SEARCH_HTML, delay=0), 1)

    def test_load_products_csv(self):
        products = tracker.load_products(Path(__file__).parent.parent / "products.csv")
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].official_price, 99000)
        self.assertEqual(products[1].official_price, 199000)
        # 상품명 표기(영문/한글)가 제각각이라 모델 번호로 고정한다
        self.assertEqual(products[0].include, ["MXK53KH"])
        self.assertEqual(products[1].include, ["MXCK3KH"])


if __name__ == "__main__":
    unittest.main()
