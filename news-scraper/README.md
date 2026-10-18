# news-scraper

매일 자정(00:00)에 **전날 주요기사 Top 10**을 RSS로 수집해 Google Sheets에 추가한다. Claude API는 쓰지 않는다(비용 없음).

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
git clone -b claude/repository-selection-check-4zcifg https://github.com/kywon01/project.git ~/project
cd ~/project/news-scraper
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scraper.py --dry-run     # 업로드 없이 수집 확인
.venv/bin/python scraper.py               # 실제 업로드 확인
```

## 3. 자정 자동 실행 (launchd)
```bash
sed -i '' "s/YOUR_NAME/$(whoami)/g" com.user.news-scraper.plist
cp com.user.news-scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.news-scraper.plist
launchctl start com.user.news-scraper     # 즉시 1회 테스트
```
- 맥 시간대가 한국(KST)이어야 0시에 실행된다.
- 잠자기 상태면 깨어난 뒤 실행된다. 23:55에 깨우려면: `sudo pmset repeat wakeorpoweron MTWRFSU 23:55:00`
- 로그: `scraper.log`
- 해제: `launchctl unload ~/Library/LaunchAgents/com.user.news-scraper.plist`

## 옵션
- `python scraper.py --date 2026-10-01` 특정 날짜 수집
- 피드 추가/삭제, 개수 변경은 `config.json`
- 테스트: `pip install pytest && pytest tests`

## 간편 설치/점검 (맥미니)
```bash
git pull
./install.sh           # venv, 패키지, launchd 예약(기본 00:00)을 한 번에 설정
./install.sh 17 0      # 시험용: 17:00으로 등록
./status.sh            # 현재 상태 한눈에 확인
```

## 선정 규칙 / 알림 (config.json)
- `keywords`: 제목에 이 키워드가 든 기사를 먼저 채운다. 모자라면 나머지 기사로 채운다.
  `strict_keywords`를 `true`로 하면 키워드 기사만 올린다(10건 미만이 될 수 있음).
- 같은 주제로 보이는 제목(단어 4개 이상, 짧은 쪽의 60% 이상 겹침)은 하나만 남긴다.
  `similar_min_common`, `similar_ratio`로 조절한다.
- `log_worksheet`(기본 `Log`): 시트의 `Log` 탭에 실행마다 `OK/WARN/ERROR`와 메시지를 남긴다.
- 최근 7일 안에 빠진 기사일이 있으면 `WARN`으로 기록하고 알린다.
- `notify.macos`: 실패/경고 시 맥 알림 센터로 알린다(맥에 로그인된 상태에서만 보임).
- 파이썬이 시작조차 못 하는 오류(예: 폴더 권한)는 Log 탭에 남지 않는다. 아침에 `./status.sh`와 시트로 확인한다.
- `sort_desc`(기본 `true`): 실행할 때마다 `Top10` 탭을 기사일 내림차순(같은 날은 순위 오름차순)으로 정렬한다.
