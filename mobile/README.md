# 툭 타 — React Native (Expo) 앱

Streamlit 프로토타입(`../`)을 React Native로 이식하는 프로젝트입니다.
**현재: 홈 → 경로 탐색 → 경로 상세** 3개 화면 + 네비게이션까지 구현되어 있습니다.

## 아키텍처

```
React Native (Expo)  ──HTTP──▶  FastAPI (../backend/main.py)  ──▶  services/ (Python 로직 재사용)
        │
   화면(UI)만 새로 구현            기존 경로/저상/지하철 로직 그대로
```

핵심 로직(저상버스 판별·경로 정렬·출구 추론·AI 브리핑)은 Python `services/`에 그대로 두고,
앱은 백엔드 HTTP API를 호출하는 **프론트엔드 교체** 방식입니다.

## 실행 방법

### 1) 백엔드 (프로젝트 루트에서)

```bash
cd ..
uvicorn backend.main:app --reload --port 8000
```

`http://localhost:8000/health` 가 `{"status":"ok"}` 면 정상입니다.

### 2) 앱 (이 폴더에서)

```bash
npm install          # 최초 1회
npx expo start       # 개발 서버
#  → i (iOS 시뮬레이터) / a (Android 에뮬레이터) / w (웹)
#  → 또는 폰의 Expo Go 앱으로 QR 스캔
```

### 백엔드 주소 설정 (중요)

`src/api/client.ts` 의 `BASE_URL`:

| 실행 환경 | 주소 |
|---|---|
| 웹 / iOS 시뮬레이터 | `http://localhost:8000` (기본) |
| Android 에뮬레이터 | `http://10.0.2.2:8000` (자동) |
| **실기기 (Expo Go)** | 같은 와이파이의 PC 내부 IP — `EXPO_PUBLIC_API_URL=http://192.168.0.x:8000` 환경변수로 지정 |

## 현재 구현

- `src/theme.ts` — 네이비 테마 토큰 (접근성: 최소 글자 18px, 터치 48dp)
- `src/data/favorites.ts` — 자주 가는 곳 / 기본 출발지
- `src/data/modes.ts` — 경로 모드(빠른길/휠체어/덜걷기)
- `src/api/client.ts` — 백엔드 클라이언트 전체 (geocode, routes/search, bus, subway, facilities, briefing)
- `src/components/` — FavoriteCard · ModeCard · RouteCard · StepCard · RouteMap
- `src/screens/HomeScreen.tsx` — 로고 · 자주 가는 곳 · 출발/도착 검색 · 경로 찾기
- `src/screens/RoutesScreen.tsx` — 모드 카드 + 경로 검색 결과 리스트
- `src/screens/DetailScreen.tsx` — 카카오맵 + 단계별 안내 + 버스/지하철 실시간 도착 + AI 브리핑
- `src/navigation/` — `@react-navigation/native-stack` (Home → Routes → Detail)

### 카카오맵 (RouteMap)

- 카카오맵 JS SDK를 WebView(네이티브) / iframe(웹)에 주입, ODsay `lane` 폴리라인 + 출발·도착 마커.
- JS 키는 백엔드 `/config`에서 받아옵니다 (`.env`의 `KAKAO_JS_KEY` 또는 `KAKAO_SDK_DOMAIN`).
- **중요**: 카카오맵 SDK는 [카카오 개발자 콘솔 > 내 애플리케이션 > 플랫폼]에 **등록된 도메인에서만** 동작합니다.
  지도가 "불러올 수 없습니다"로 뜨면 사용 중인 도메인(웹: `http://localhost:8081` 등)을 Web 플랫폼에 등록하세요.
  네이티브 WebView는 `baseUrl: https://localhost` 로 로드합니다.

**동작 흐름**: 홈에서 즐겨찾기/도착지 검색 → `/geocode` 좌표 변환 → 경로 탐색(`/routes/search`)
→ 경로 카드 선택 → 상세 화면에서 단계별 안내 + 버스(`/bus/arrivals`·`/bus/low-floor`)·
지하철(`/subway/station-codes`→`/subway/next-trains`) 실시간 도착 + AI 브리핑(`/briefing`) 표시.

## 백엔드 API (../backend/main.py)

services/ 로직이 전부 HTTP로 노출되어 있습니다:
`/geocode` `/routes/search` `/routes/lane` `/walk/pedestrian`
`/bus/arrivals` `/bus/low-floor`
`/subway/station-codes` `/subway/next-trains` `/subway/facilities` `/subway/place-id` `/subway/url`
`/briefing`

API 문서: 백엔드 실행 후 `http://localhost:8000/docs`

## 구현 완료 기능

- ✅ 홈 → 경로 탐색 → 경로 상세 3개 화면 + 네비게이션
- ✅ 카카오맵(폴리라인·마커), 버스/지하철 실시간 도착, AI 브리핑
- ✅ **휠체어 정밀 정렬** — 저상버스 친화도 점수화(`/routes/score-low-floor`), tier 기반 정렬 + 저상 배지
- ✅ **지하철 교통약자 시설 패널** — KRIC 엘리베이터 출구 안내(`/subway/facilities`)
- ✅ **GPS 현재위치** — `expo-location`으로 출발지 자동 설정(`/reverse-geocode`)
- ✅ **음성 안내(TTS)** — `expo-speech`로 AI 브리핑 읽어주기

## 다음 단계 (예정)

1. **푸시 알림** — 버스 도착 알림 (별도 푸시 서버·인증서 필요)
2. **지도 도메인 등록** — 카카오 개발자 콘솔에 실제 배포 도메인 등록
3. **앱 빌드/배포** — EAS Build로 스토어 배포
