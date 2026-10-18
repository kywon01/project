# To-do List 웹앱

Flask REST API 백엔드와 바닐라 JS 프론트엔드로 구성된 간단한 To-do 리스트 웹앱입니다.

## 구조

```
backend/    Flask API 서버 (SQLite 저장소)
frontend/   정적 HTML/CSS/JS 프론트엔드
```

## 실행 방법

Flask가 API와 프론트엔드 정적 파일을 함께 서빙하므로 **터미널 하나, 명령어 하나**면 됩니다.

```bash
cd backend
pip3 install -r requirements.txt
python3 app.py
```

(Windows나 `python` 명령어가 파이썬 3를 가리키는 환경이라면 `pip`/`python`을 그대로 사용해도 됩니다.)

브라우저에서 `http://localhost:5001` 으로 접속하면 앱이 바로 뜹니다. (별도 빌드 과정 없음)

> macOS는 포트 5000을 AirPlay 수신 기능이 기본으로 점유하고 있어 Flask와 충돌할 수 있습니다. 이 프로젝트는 이를 피하기 위해 5001 포트를 사용합니다.

## 기능

- 할 일 추가/완료 토글/삭제
- 마감일 지정 (지난 마감일은 빨간색으로 표시)
- 우선순위 (낮음/보통/높음)
- 카테고리 분류 (자유 입력, 기존 카테고리 자동완성)
- 제목 검색 및 카테고리/우선순위 필터

## API

| Method | Endpoint          | 설명           |
|--------|-------------------|----------------|
| GET    | /api/todos        | 목록 조회 (쿼리 파라미터: `search`, `category`, `priority`) |
| GET    | /api/categories   | 사용 중인 카테고리 목록 |
| POST   | /api/todos        | 할 일 추가 (`title`, `due_date`, `priority`, `category`) |
| PUT    | /api/todos/{id}   | 수정 (완료 토글 등) |
| DELETE | /api/todos/{id}   | 삭제           |

> DB 스키마는 실행 시 자동으로 마이그레이션되므로 기존 `backend/todos.db`를 지우지 않아도 됩니다.
