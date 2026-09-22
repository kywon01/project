# To-do List 웹앱

Flask REST API 백엔드와 바닐라 JS 프론트엔드로 구성된 간단한 To-do 리스트 웹앱입니다.

## 구조

```
backend/    Flask API 서버 (SQLite 저장소)
frontend/   정적 HTML/CSS/JS 프론트엔드
```

## 실행 방법

### 백엔드

```bash
cd backend
pip3 install -r requirements.txt
python3 app.py
```

(Windows나 `python` 명령어가 파이썬 3를 가리키는 환경이라면 `pip`/`python`을 그대로 사용해도 됩니다.)

`http://localhost:5000` 에서 API가 실행됩니다.

### 프론트엔드

`frontend/index.html`을 `file://`로 직접 열면 최신 브라우저(Chrome 등)의 보안 정책(Private Network Access)에 막혀 API 호출이 CORS 에러로 실패할 수 있습니다. 대신 간단한 로컬 웹서버로 열어주세요.

```bash
cd frontend
python3 -m http.server 5500
```

그 다음 브라우저에서 `http://localhost:5500` 으로 접속합니다. (별도 빌드 과정 없음)

## API

| Method | Endpoint          | 설명           |
|--------|-------------------|----------------|
| GET    | /api/todos        | 목록 조회      |
| POST   | /api/todos        | 할 일 추가     |
| PUT    | /api/todos/{id}   | 수정 (완료 토글 등) |
| DELETE | /api/todos/{id}   | 삭제           |
