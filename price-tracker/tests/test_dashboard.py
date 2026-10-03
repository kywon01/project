import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import dashboard
import db
import tracker


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.connect(str(Path(self.tmp.name) / "t.db"))
        self.product = tracker.Product("마우스", "q", "", 99000, 88000, [], [])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_build_data_orders_rows_oldest_first(self):
        db.save_price(self.conn, "마우스", 99000, "A", "")
        db.save_price(self.conn, "마우스", 95000, "B", "")
        data = dashboard.build_data([self.product], self.conn)
        rows = data["products"][0]["rows"]
        self.assertEqual([r["price"] for r in rows], [99000, 95000])
        self.assertEqual(data["products"][0]["official"], 99000)
        self.assertEqual(data["products"][0]["target"], 88000)

    def test_product_without_history_has_empty_rows(self):
        self.assertEqual(dashboard.build_data([self.product], self.conn)["products"][0]["rows"], [])

    def test_render_escapes_script_end_tag_in_untrusted_names(self):
        db.save_price(self.conn, "마우스", 99000, "</script><script>alert(1)</script>", "")
        html = dashboard.render(dashboard.build_data([self.product], self.conn))
        # 스크립트 블록을 끝내는 </script>는 템플릿의 것 하나뿐이어야 한다
        self.assertEqual(html.count("</script"), 1)
        payload = re.search(r"const DATA = (.*?);\n", html, re.S).group(1)
        self.assertEqual(json.loads(payload)["products"][0]["rows"][0]["matched"], "</script><script>alert(1)</script>")

    def test_render_replaces_placeholder(self):
        html = dashboard.render(dashboard.build_data([self.product], self.conn))
        self.assertNotIn("__DATA__", html)


if __name__ == "__main__":
    unittest.main()
