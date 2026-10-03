"""RSS 후보 주소를 한꺼번에 점검한다: python check_feeds.py"""
import feedparser

CANDIDATES = [
    ("전자신문 Section901", "https://rss.etnews.com/Section901.xml"),
    ("전자신문 Section902", "https://rss.etnews.com/Section902.xml"),
    ("전자신문 Section903", "https://rss.etnews.com/Section903.xml"),
    ("ZDNet Korea", "https://feeds.feedburner.com/zdkorea"),
    ("블로터 allArticle", "https://www.bloter.net/rss/allArticle.xml"),
    ("디지털데일리", "https://www.ddaily.co.kr/rss/allArticle.xml"),
    ("디지털투데이", "https://www.digitaltoday.co.kr/rss/allArticle.xml"),
    ("아이티데일리", "https://www.itdaily.kr/rss/allArticle.xml"),
    ("보안뉴스", "https://www.boannews.com/media/news_rss.xml"),
    ("한국경제 IT", "https://www.hankyung.com/feed/it"),
    ("IT동아", "https://it.donga.com/feeds/rss/"),
    ("연합뉴스 IT", "https://www.yna.co.kr/rss/it.xml"),
    ("연합뉴스 경제", "https://www.yna.co.kr/rss/economy.xml"),
]

for name, url in CANDIDATES:
    p = feedparser.parse(url, agent="Mozilla/5.0 news-scraper")
    n = len(p.entries)
    if n:
        first = p.entries[0]
        print(f"OK   {name:<18} {n:>3}건 | {first.get('published', '?')} | {first.title[:40]}")
    else:
        print(f"FAIL {name:<18} {url}")
