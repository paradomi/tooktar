# 툭 타 — 웹 배포 가이드 (QR → 웹앱)

구성: 프론트(Expo 웹, Vercel) + 백엔드(FastAPI, Render). 둘 다 무료 티어, GitHub(paradomi/tooktar) 연동 자동 배포.

## 1. 백엔드 — Render (약 10분)

1. https://render.com 접속 → **GitHub 계정으로 로그인**
2. 대시보드 → **New → Blueprint** → 저장소 `paradomi/tooktar` 선택
3. `render.yaml`을 자동 인식 → 서비스 이름 `tooktah-api` 확인 → **Apply**
4. 환경변수 입력 화면에서 PC의 `.env` 값을 그대로 복사해 입력:
   - `GBIS_API_KEY`, `ODSAY_API_KEY`, `KAKAO_REST_API_KEY`, `KAKAO_SDK_DOMAIN`, `TMAP`, `KRIC`, `Gemini`
5. 빌드 완료(5분쯤) 후 URL 확인: `https://tooktah-api.onrender.com` 형태
6. 브라우저에서 `https://<백엔드URL>/health` 접속 → `{"status":"ok"}` 나오면 성공

※ 무료 티어는 15분 무접속 시 잠들고, 첫 접속에 30~50초 걸림 (발표 직전에 한 번 접속해 깨워둘 것)

## 2. 프론트 — Vercel (약 5분)

1. https://vercel.com 접속 → **GitHub 계정으로 로그인**
2. **Add New → Project** → `paradomi/tooktar` Import
3. 설정:
   - **Root Directory**: `mobile` (Edit 눌러 변경 — 중요!)
   - Framework Preset: Other (vercel.json이 빌드 설정을 대신함)
4. **Environment Variables** 추가:
   - `EXPO_PUBLIC_API_URL` = `https://<1번에서 받은 Render 백엔드 URL>`
5. **Deploy** → 완료 후 URL 확인: `https://tooktar-xxx.vercel.app` 형태

## 3. 카카오 지도 도메인 등록 (1분)

1. https://developers.kakao.com → 내 애플리케이션 → 앱 선택
2. **플랫폼 → Web → 사이트 도메인**에 Vercel URL 추가 (예: `https://tooktar-xxx.vercel.app`)
   - 미등록 시 지도만 안 뜨고 나머지는 동작함

## 4. QR 코드

Vercel URL이 나오면 Claude에게 "QR 만들어줘"라고 요청 → PNG 생성해 포스터에 삽입.

## 이후 업데이트

`git push origin main` 하면 Render·Vercel 모두 자동 재배포됨.

## 문제 해결

- 경로 검색이 안 됨 → Render 환경변수 누락/오타 확인 (특히 `TMAP`, `KRIC`, `Gemini`는 약식 이름)
- 지도가 안 뜸 → 카카오 콘솔 Web 도메인에 Vercel URL 등록 여부 확인
- 처음 접속이 느림 → Render 무료 티어 콜드스타트 (정상)
