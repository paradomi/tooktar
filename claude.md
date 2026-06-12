# 툭 타 (Took-Tah) - 교통약자 전용 대중교통 앱

## 프로젝트 개요
- 교통약자(휠체어, 유모차, 고령자, 시각장애인)를 위한 배리어프리 대중교통 안내 웹앱
- Streamlit + Python 기반, 발표용 프로토타입 (Level 3)
- 배포: Streamlit Community Cloud (https://github.com/paradomi/onetouch)

## 기술 스택
- Python 3.11, Streamlit (멀티페이지)
- FastAPI 백엔드 (`backend/main.py`) — services/ 함수를 HTTP로 노출, 향후 React 마이그레이션 대비
- 라이브러리: streamlit, requests, pandas, python-dotenv, folium, streamlit-folium, streamlit-searchbox, fastapi, uvicorn[standard]
- 공공 API: 경기도 GBIS(버스도착/노선/위치/정류장), 국토부 TAGO(전국 버스), KRIC 레일포털(역사 교통약자 시설), 국가철도공단 운행시각표(승인 대기)
- 외부 API: ODsay 대중교통, Tmap 보행자, 카카오 로컬·맵 SDK
- AI: Google Gemini 2.5/2.0/1.5 Flash (Vision, fallback 체인)
- 환경변수: .env 파일 (절대 커밋하지 말 것)

## 핵심 설계 원칙
- 모든 터치 영역 최소 48x48dp, 글자 크기 18px 이상
- 고대비 색상, 메인 컬러 #1f77b4
- session_state 키 규칙: 위젯용은 _input 접미사, 데이터 전달용은 selected_ 접두사
- 카카오맵 교통약자 탭은 API 비공개 → KRIC/서울교통공사 공공데이터로 대체
- 저상버스 필터링은 경기도 API의 lowPlate 필드 사용

## 주의사항
- .env 파일 절대 git에 커밋하지 말 것
- Streamlit Cloud 배포 시 secrets는 st.secrets로 읽기
- 공공 API 응답이 XML일 수 있음, format=json 파라미터 확인
- git push 전 반드시 git status로 .env 포함 여부 확인

## 코딩 규칙

### Streamlit 규칙
- st.session_state에서 위젯 key와 데이터 key 절대 겹치지 말 것
  - 위젯용: `_input` 접미사 (예: destination_input)
  - 데이터 전달용: `selected_` 접두사 (예: selected_destination)
- 페이지 간 이동은 st.switch_page() 사용
- 페이지 파일에서 상위 폴더 import 시 반드시 sys.path 추가:
```python
  import sys, os
  sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
- CSS 커스텀은 components/styles.py의 apply_global_styles()에 집중
- 새 페이지 추가 시 반드시 apply_global_styles()와 render_header() 호출

### API 호출 규칙
- 모든 API 호출은 try-except로 감싸고, 실패 시 더미 데이터로 fallback
- API 키는 os.getenv()로 읽되, Streamlit Cloud용 st.secrets도 fallback:
```python
  key = os.getenv("GBIS_API_KEY") or st.secrets.get("GBIS_API_KEY", "")
```
- 공공데이터 API는 응답이 XML일 수 있음. 항상 dataType=JSON 또는 format=json 파라미터 포함
- API 응답은 반드시 status_code 확인 후 파싱
- 시연용 fallback 데이터를 data/dummy_data.py에 항상 유지

### 파일 수정 규칙
- 기존 파일 수정 시 전체 덮어쓰기 하지 말고 변경 부분만 수정
- 새 유틸 함수는 utils/ 폴더에, 새 컴포넌트는 components/ 폴더에
- 새 파일 만들 때 상단에 한 줄 docstring 필수: """파일 설명"""
- requirements.txt에 새 라이브러리 추가 시 버전 고정하지 말 것 (Streamlit Cloud 호환)

### Git 규칙
- commit 전 반드시 git status로 .env 포함 여부 확인
- commit 메시지는 한국어로, 변경 내용 한 줄 요약
- .env, venv/, __pycache__/는 절대 커밋하지 말 것

### 테스트
- API 연동 코드는 먼저 독립 테스트 스크립트로 확인 후 본 앱에 통합
- streamlit run app.py로 로컬 테스트 후 push

## 프로젝트 구조 (현행)
```
app.py                       # 홈/검색 (네이비 테마)
pages/
  1_경로_탐색.py             # 모드 카드(fast/wheel/walk_less), 경로 리스트
  2_경로_상세.py             # 지도, 단계 안내, KRIC 시설, AI 브리핑, 출구 자동 판별
  3_설정.py                  # 자주 가는 곳 편집 등
components/
  styles.py                  # apply_global_styles() — 글로벌 CSS
  header.py                  # render_header() — 메인 화면 전용
  route_card.py              # HTML+버튼 카드 (bus_arrival, lf_score 표시)
services/
  geocode.py                 # 카카오 주소→좌표
  kakao_local.py             # 키워드 검색, place_id, 출구 좌표
  odsay_api.py               # 대중교통 경로 + steps 파싱
  tmap_api.py                # 보행자 경로 (searchOption=4 계단회피)
  bus_arrival.py             # GBIS + TAGO 통합, 저상버스 3단계 판별
  rail_portal.py             # KRIC 역사 이동/엘리베이터/리프트
  subway_arrival.py          # B551457 운행정보 (현재 사용 불가, fallback 빈 리스트)
  ai_briefing.py             # 템플릿 브리핑 + Gemini Vision 도면 분석
backend/
  main.py                    # FastAPI — /health /geocode /routes/search /routes/lane /walk/pedestrian /subway/*
data/
  dummy_data.py              # FAVORITE_PLACES (좌표 사전 저장)
  station_codes.csv          # KRIC 역코드 1108개
  tago_city_codes.csv        # TAGO 도시코드 133개
  odsay_api.py               # (legacy, services/odsay_api.py가 정식)
```

## API 상세 정보

### 경기도 GBIS (services/bus_arrival.py)
- 버스도착: `http://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2`
- 버스노선: `http://apis.data.go.kr/6410000/busrouteservice/v2/getBusRouteListv2`
- 버스위치: `getBusLocationListv2` (저상 확인용)
- 정류장: `getBusStationListv2` (이름+좌표로 stationId 역추적)
- 필수: serviceKey, format=json
- 저상버스 필드: `lowPlate1`, `lowPlate2` (1=저상). 0이어도 노선/위치 fallback으로 재확인

### 국토부 TAGO (전국 버스, 경기 외)
- 도착: `ArvlInfoInqireService` / 정류장: `BusSttnInfoInqireService`
- city_code는 `data/tago_city_codes.csv`에서 좌표→카카오 region→매핑

### KRIC 레일포털 (services/rail_portal.py)
- `getStationMovement`, `getElevatorMovement`, `getTransferMovement`, `getWheelchairLift`
- 키 파라미터: railOprIsttCd(운영기관), lnCd(노선), stinCd(역) — `data/station_codes.csv` 참조

### 국가철도공단 운행시각표 (지하철 도착, 승인 대기)
- B551457 run/v2는 분당선 미포함 + 과거 데이터만 → 미사용 확정
- 승인 시 별도 엔드포인트로 `services/subway_arrival.py` 재구현 예정

### ODsay 대중교통 길찾기
- Base URL: `https://api.odsay.com/v1/api/searchPubTransPathT`
- 필수: SX, SY, EX, EY, apiKey
- `parse_path_to_steps`에 startID/start_x/start_y/end_x/end_y 포함 (GBIS 매칭·출구 추론용)
- 정류장명에 "N번출구" 포함 시 출구 추론 Tier 1로 사용

### Tmap 보행자 경로
- `searchOption=4`: 계단 회피 경로 (휠체어 모드 필수)

### 카카오 로컬 API
- 주소 → 좌표: `https://dapi.kakao.com/v2/local/search/address`
- 키워드 검색: `https://dapi.kakao.com/v2/local/search/keyword` (category_group_code SW8 = 지하철)
- 출구 좌표: `"{역명} N번 출구"` N=1..12 키워드 검색
- 헤더: `Authorization: KakaoAK {REST_API_KEY}`

### Gemini Vision (services/ai_briefing.py)
- `google-genai` SDK, `client.models.generate_content`
- 모델 fallback: gemini-2.5-flash → 2.0-flash → 1.5-flash (503/429 시)
- 입력: KRIC imgPath PNG (https로 강제 변환), 프롬프트는 휠체어 이용자 관점 4~5문장 안내

## 자주 하는 실수 방지
- Streamlit은 버튼 클릭 시 전체 스크립트가 재실행됨. 무거운 API 호출은 @st.cache_data 사용
- st.link_button()은 외부 링크용, 내부 페이지 이동은 st.switch_page()
- HTML 렌더링 시 unsafe_allow_html=True 필수
- 한글 파일명(예: 1_경로_탐색.py)은 import 시 문제 가능 → sys.path 방식 사용
- HTML 카드 내부에 4-space 들여쓰기 금지 (markdown이 코드블록으로 렌더링) — 한 줄 concatenation
- streamlit-elements는 콜백 버그로 사용 금지, st.markdown(HTML) + st.button 조합 사용
- streamlit-searchbox는 `rerun_on_update=True` (False면 드롭다운 안 뜸)
- 휠체어 모드의 GBIS 병렬 호출은 ThreadPoolExecutor 사용 (로딩 시간 단축)
- 환경변수 `Gemini`는 대문자 G만 (다른 키는 모두 UPPER_SNAKE)

# 작업 분담 지침

## 역할 분리
- **Opus 4.7 (메인)**: 코드 설계, 구현 계획 수립, 작성된 코드 검사/리뷰
- **Sonnet 4.6 (서브 에이전트)**: 실제 코드 작성/편집

## 진행 방식
1. Opus가 사용자 요구를 분석하고 구현 계획(어떤 파일을, 어떻게 수정할지)을 세운다.
2. Opus는 직접 Edit/Write를 하지 않고, Agent 도구로 sonnet 4.6 에이전트를 호출해 구체적인 코드 작성 지시를 내린다.
3. Sonnet 에이전트가 작성을 마치면 Opus가 변경된 파일을 읽어 검사하고, 필요하면 추가 수정을 다시 sonnet에게 지시한다.

## 예외
- 환경 변수 확인, 단순 파일 읽기/조회, git 상태 확인 등 검토·계획 단계의 read-only 작업은 Opus가 직접 수행해도 된다.

# 세션 누적 결정사항 (Session Decisions Log)

이 섹션은 이전 세션에서 결정·구현된 내용을 다음 세션이 잊지 않도록 누적 기록한다. 새 결정이 생기면 위에 prepend.

## UI / UX 결정
- **헤더 로고**: 메인 화면에만 표시, 다른 페이지에서는 제거
- **카드 디자인**: streamlit-elements 사용 금지 (콜백 버그) → st.markdown(HTML) + st.button 조합
- **카드 내부 HTML**: 4-space 들여쓰기 금지 (markdown이 코드블록으로 렌더). 한 줄 concatenation으로 작성
- **글자 크기**: 도착시간·저상 라벨은 원본 대비 1.5배 (2배는 과함)
- **정류장 표시 포맷**: `00정류소 | 00방면` + Gowun Batang 바탕체 폰트 (Google Fonts CDN)
- **버스 안내 문구**: `00승차 00정거장 00분 이동` 형식
- **지하철 방면 표시**: `(종점, 인접역) 방면` 형식 (예: "청량리, 매탄권선 방면") — 실제 지하철 안내표지판과 동일
- **지도**: 카카오맵 ROADMAP(일반지도) 기본, 일반/위성 토글 제공
- **확대**: 모바일 핀치 줌, 데스크톱 스크롤 줌
- **버스 도착 정보**: 모든 모드(fast/wheel/walk_less)에서 표시 (휠체어 전용 아님)
- **메인 화면**: 자주 가는 곳 카드에도 버스 도착·저상 정보 표시
- **자동완성**: streamlit-searchbox 사용, `rerun_on_update=True` (False면 깨짐)
- **⚠️ 이모지**: 의미 없으면 사용 금지 (사용자 명시 거부)

## 핵심 기능 구현
- **계단회피 도보**: Tmap pedestrian API `searchOption=4` 사용
- **저상버스 판별 3단계**: lowPlate1/2 → BusLocation 차량위치 → BusRoute 키워드 검색
- **휠체어 모드 정렬**: 30분 내 저상버스 도착 경로 우선, ThreadPoolExecutor 병렬 호출
- **지하철-only 경로**: 저상버스 라벨 표시 금지 (lf_score None 처리)
- **ODsay ↔ GBIS 정류장 매칭**: startID 불일치 시 이름+좌표 fallback (`gbis_find_station_id`)
- **TAGO 전국 확장**: 경기도 외 지역은 ArvlInfoInqireService + BusSttnInfoInqireService
- **AI 브리핑**: 1단계 템플릿(`services/ai_briefing.py:generate_briefing`) + 2단계 Gemini Vision 도면 분석(`analyze_subway_diagram`)
- **Gemini 모델 fallback**: 2.5-flash → 2.0-flash → 1.5-flash (503/429 시)
- **지하철 출구 자동 판별** (`pages/2_경로_상세.py:_infer_subway_exits`):
  - Tier 1: 정류장명 정규식 `(\d+)번\s*출구`
  - Tier 2: Kakao로 `{역명} N번 출구` N=1..12 검색해 좌표 비교 (`kakao_local.find_station_exits`, `find_nearest_exit`)
  - KRIC 패널 selectbox에 `✓ 추천` 자동 선택, AI 브리핑 상단에 출구 명시

## API 상태
- **B551457 한국철도공사 run/v2** (지하철 도착): 권한 받았으나 분당선 미포함 + 과거 데이터만 → 미사용
- **국가철도공단 역사별 운행시각표** (Option C): 신청 대기 중 → 승인 후 구현 예정
- **KRIC 교통약자 시설**: API key 보유, `data/station_codes.csv`에 1108개 역코드
- **TAGO city codes**: `data/tago_city_codes.csv` 133개

## 미해결 / 차기 작업
- 지하철 도착시간: 국가철도공단 API 승인 후 구현
- Streamlit Cloud 배포 (tooktar.streamlit.app): 사용자 보류

## 환경변수 키 이름 (절대 변경 금지)
- `GBIS_API_KEY`, `ODSAY_API_KEY`, `KAKAO_REST_API_KEY`, `TMAP_API_KEY`, `KRIC_API_KEY`, `Gemini` (Gemini는 대문자 G만)

## 데이터 고정값
- `data/dummy_data.py`의 FAVORITE_PLACES 좌표 사전 저장됨
- 집 = 우남1차아파트 (127.03362843525207, 37.247332166005776) — 수원역 아님
