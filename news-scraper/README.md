# news-scraper

매일 새벽 6시에 **전날 주요기사 Top 10**을 RSS로 수집해 Google Sheets에 추가한다. Claude API는 쓰지 않는다(비용 없음).

## 동작
- `config.json`의 RSS 피드에서 전날(KST) 기사만 골라 매체별로 번갈아 10건을 뽑는다. 제목/링크 중복은 제거한다.
- RSS에는 조회수가 없어 "주요기사 순위"는 각 피드의 노출 순서를 따른다.
- 같은 기사일이 시트에 이미 있으면 다시 추가하지 않는다(재실행 안전).
- 시트 컬럼: 수집일, 기사일, 순위, 제목, 출처, 링크, 발행시각

## 1. Google 설정 (최초 1회)
1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트 생성 → **Google Sheets API** 사용 설정
2. IAM → 서비스 계정 생성 → 키(JSON) 발급 → `news-scraper/service_account.json`으로 저장
3. Google 시트를 새로 만들고, 서비스 계정 이메일(`...@...iam.gserviceaccount.com`)에 **편집자**로 공유
4. 시트 URL의 `/d/<여기>/edit` 부분을 `config.json`의 `spreadsheet_id`에 입력

`service_account.json`은 `.gitignore`에 들어 있다. 저장소에 올리지 말 것.

## 2. 맥미니 설치
```bash
git clone https://github.com/kywon01/project.git ~/project
cd ~/project/news-scraper
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scraper.py --dry-run     # 업로드 없이 수집 확인
.venv/bin/python scraper.py               # 실제 업로드 확인
```

## 3. 새벽 6시 자동 실행 (launchd)
```bash
sed -i '' "s/YOUR_NAME/$(whoami)/g" com.user.news-scraper.plist
cp com.user.news-scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.news-scraper.plist
launchctl start com.user.news-scraper     # 즉시 1회 테스트
```
- 맥 시간대가 한국(KST)이어야 6시에 실행된다.
- 잠자기 상태면 깨어난 뒤 실행된다. 새벽 5:55에 깨우려면: `sudo pmset repeat wakeorpoweron MTWRFSU 05:55:00`
- 로그: `scraper.log`
- 해제: `launchctl unload ~/Library/LaunchAgents/com.user.news-scraper.plist`

## 옵션
- `python scraper.py --date 2026-10-01` 특정 날짜 수집
- 피드 추가/삭제, 개수 변경은 `config.json`
- 테스트: `pip install pytest && pytest tests`
