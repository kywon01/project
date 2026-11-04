#!/usr/bin/env python3
"""가격 이력을 보여주는 웹 대시보드(dashboard.html)를 만든다.

    python3 dashboard.py          # dashboard.html 생성
    python3 dashboard.py --open   # 생성 후 브라우저로 열기

서버 없이 파일 하나로 열리고, 인터넷 연결이나 추가 라이브러리가 필요 없다.
"""
import argparse
import json
import webbrowser
from datetime import datetime
from pathlib import Path

import db
import tracker

HERE = Path(__file__).parent
TEMPLATE = HERE / "dashboard_template.html"


def build_data(products: list[tracker.Product], conn) -> dict:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "products": [
            {
                "name": p.name,
                "official": p.official_price,
                "target": p.target_price,
                "rows": [
                    {"at": at, "price": price, "matched": matched or ""}
                    for at, price, matched in db.all_rows(conn, p.name)
                ],
            }
            for p in products
        ],
    }


def render(data: dict, template: Path = TEMPLATE) -> str:
    # 상품명/매칭된 이름은 외부에서 온 값이라 </script>가 섞여도 페이지가 깨지지 않게 이스케이프한다.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.read_text(encoding="utf-8").replace("__DATA__", payload)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products", type=Path, default=HERE / "products.csv")
    ap.add_argument("--db", default=str(HERE / "prices.db"))
    ap.add_argument("--out", type=Path, default=HERE / "dashboard.html")
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    args = ap.parse_args(argv)

    conn = db.connect(args.db)
    args.out.write_text(render(build_data(tracker.load_products(args.products), conn)), encoding="utf-8")
    print(f"대시보드를 만들었어요: {args.out}")
    if args.open:
        webbrowser.open(args.out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
