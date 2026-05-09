# 툭타 백엔드 (FastAPI)

`services/` 함수를 HTTP 엔드포인트로 노출합니다. streamlit과는 독립 프로세스로 동작합니다.

## 실행

```bash
# 프로젝트 루트에서
uvicorn backend.main:app --reload --port 8000
```

브라우저:
- API 문서: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

## 엔드포인트

- `GET /health` — 헬스체크
- `GET /geocode?address=수원시청` — 주소 → 좌표
- `POST /routes/search` — 대중교통 경로 검색 (ODsay)
- `GET /routes/lane?map_obj=...` — 폴리라인 좌표 (ODsay loadLane)
- `POST /walk/pedestrian` — 도보 경로 (Tmap)
- `GET /subway/place-id?name=수원시청` — 역 → 카카오 place_id
- `GET /subway/url?name=수원시청` — 역 → 카카오맵 교통약자 페이지 URL

## CORS

개발용으로 `*` 모두 허용. 운영 배포 시 `backend/main.py`에서 `allow_origins`를 도메인 제한으로 변경하세요.
