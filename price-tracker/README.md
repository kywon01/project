# 다나와 가격 추적기

애플 Magic Mouse(USB-C)와 Touch ID Magic Keyboard(USB-C, 한국어)의 다나와 최저가를 수집해 SQLite에 이력으로 쌓고,
목표가 도달·공식가 대비 할인·가격 하락 시 터미널에 알려 줍니다.

## 실행

```bash
cd price-tracker
pip3 install -r requirements.txt
python3 tracker.py run        # 가격 수집 + 알림
python3 tracker.py history    # 저장된 이력 보기
python3 -m unittest discover -s tests   # 테스트
```

## 웹 대시보드

```bash
python3 dashboard.py --open    # dashboard.html을 만들고 브라우저로 열기
```

- 상품별 카드에 현재 최저가, 공식가 대비, 목표가까지 남은 금액, 가격 추이 차트가 나와요.
- 차트에 마우스를 올리면 그 시점의 가격과 매칭된 상품명이 보여요 (키보드 방향키도 돼요).
- 위쪽 `7일 / 30일 / 전체`로 기간을 바꿀 수 있고, 카드 아래 "표로 보기"에서 원본 값을 확인할 수 있어요.
- 서버나 인터넷 연결이 필요 없는 파일 하나짜리 페이지예요. 새 가격을 수집한 뒤 다시 실행하면 갱신돼요.
- 수집과 함께 자동 갱신하려면 cron 줄 끝에 이어 붙이세요: `... tracker.py run && python3 dashboard.py`

## products.csv

| 컬럼 | 설명 |
|---|---|
| `name` | 표시 이름 (DB 키로도 쓰이므로 바꾸면 이력이 분리됨) |
| `query` | 다나와 검색어 |
| `url` | 다나와 상품 페이지 URL. **채우면 검색 대신 이 페이지를 직접 읽음** (가장 정확) |
| `official_price` / `target_price` | 애플 공식가 / 알림받을 목표가 |
| `must_include` | 상품명에 전부 포함되어야 하는 단어 (`\|`로 구분) |

> 다나와는 같은 상품이 `APPLE Magic Mouse MXK53KH/A`, `애플코리아 … 매직 마우스 …`처럼 제각각 표기돼요. 한글 단어로 거르면 진짜 최저가 항목을 놓칠 수 있어서, **`must_include`에는 모델 번호(예: `MXK53KH`)를 넣는 걸 권장**해요.
| `must_exclude` | 하나라도 있으면 제외할 단어 (`\|`로 구분) |

## 처음 실행할 때 확인할 것

이 코드는 다나와에 접속할 수 없는 환경에서 작성되어, **파서의 선택자는 가정한 구조 기준이고 실제 페이지로 검증되지 않았습니다.**
(테스트는 직접 만든 샘플 HTML로 돌립니다.)

1. `python3 tracker.py run --save-html html/` 로 실행해 받은 HTML을 저장합니다.
2. "조건에 맞는 검색 결과가 없어요"가 나오면 출력된 후보 목록을 보고 `must_include`/`must_exclude`를 조정합니다.
   후보가 0건이면 선택자가 안 맞는 것이므로 `html/`의 파일을 열어 `parsers.py` 상단의 `*_SELECTORS`를 고칩니다.
3. 모델이 확실해지면 다나와에서 해당 상품 페이지 URL을 `url` 컬럼에 넣으세요. 검색보다 안정적입니다.

## 자동 실행 (cron)

```
0 9,21 * * * cd /경로/price-tracker && python3 tracker.py run >> run.log 2>&1
```

사이트 이용약관과 `robots.txt`를 확인하고, 실행 빈도는 하루 1~2회 정도로 유지하세요.
