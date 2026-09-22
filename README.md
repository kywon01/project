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

`frontend/index.html` 파일을 브라우저로 열면 됩니다. (별도 빌드 과정 없음)

## API

| Method | Endpoint          | 설명           |
|--------|-------------------|----------------|
| GET    | /api/todos        | 목록 조회      |
| POST   | /api/todos        | 할 일 추가     |
| PUT    | /api/todos/{id}   | 수정 (완료 토글 등) |
| DELETE | /api/todos/{id}   | 삭제           |
