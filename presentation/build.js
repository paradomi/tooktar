// 툭 타(Took-Tah) 앱 소개 발표자료 생성 스크립트
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

// ---- 팔레트 (Ocean Navy — 교통/신뢰/접근성) ----
const NAVY = "0F2E4D";      // 딥 네이비 (다크 배경)
const NAVY2 = "143A5E";     // 약간 밝은 네이비
const BLUE = "1F77B4";      // 메인 블루 (앱 메인 컬러)
const TEAL = "2EC4B6";      // 민트/틸 액센트
const LIGHT = "F4F7FB";     // 라이트 배경
const CARD = "FFFFFF";      // 카드 흰색
const GRAY = "5B6B7B";      // 본문 회색
const DARKTXT = "1B2733";   // 진한 본문
const WHITE = "FFFFFF";

const KFONT = "맑은 고딕";

// ---- 아이콘 → base64 PNG ----
async function icon(IconComponent, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

const makeShadow = () => ({ type: "outer", color: "0F2E4D", blur: 8, offset: 3, angle: 135, opacity: 0.18 });

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
  pres.author = "툭 타 팀";
  pres.title = "툭 타 (Took-Tah) 앱 소개";

  const W = 13.3, H = 7.5;

  // 아이콘 미리 렌더
  const ic = {
    wheel: await icon(fa.FaWheelchair, "#FFFFFF"),
    bus: await icon(fa.FaBus, "#FFFFFF"),
    subway: await icon(fa.FaSubway, "#FFFFFF"),
    robot: await icon(fa.FaRobot, "#FFFFFF"),
    pin: await icon(fa.FaMapMarkerAlt, "#FFFFFF"),
    bolt: await icon(fa.FaBolt, "#FFFFFF"),
    server: await icon(fa.FaServer, "#FFFFFF"),
    code: await icon(fa.FaCode, "#FFFFFF"),
    db: await icon(fa.FaDatabase, "#FFFFFF"),
    cloud: await icon(fa.FaCloud, "#FFFFFF"),
    cogs: await icon(fa.FaCogs, "#FFFFFF"),
    access: await icon(fa.FaUniversalAccess, "#FFFFFF"),
    loc: await icon(fa.FaLocationArrow, "#FFFFFF"),
    route: await icon(fa.FaRoute, "#FFFFFF"),
    clock: await icon(fa.FaClock, "#FFFFFF"),
    mic: await icon(fa.FaMicrophone, "#FFFFFF"),
    layer: await icon(fa.FaLayerGroup, "#FFFFFF"),
    door: await icon(fa.FaDoorOpen, "#FFFFFF"),
    exchange: await icon(fa.FaExchangeAlt, "#FFFFFF"),
    react: await icon(fa.FaReact, "#FFFFFF"),
    python: await icon(fa.FaPython, "#FFFFFF"),
    brain: await icon(fa.FaBrain, "#FFFFFF"),
    mobile: await icon(fa.FaMobileAlt, "#FFFFFF"),
    eye: await icon(fa.FaEye, "#FFFFFF"),
    check: await icon(fa.FaCheckCircle, "#2EC4B6"),
    handsHelping: await icon(fa.FaHandsHelping, "#FFFFFF"),
  };

  // 색 원 안에 아이콘
  function iconCircle(slide, data, x, y, d, fill) {
    slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, shadow: makeShadow() });
    const pad = d * 0.26;
    slide.addImage({ data, x: x + pad, y: y + pad, w: d - pad * 2, h: d - pad * 2 });
  }

  // 공통 헤더(라이트 슬라이드)
  function lightHeader(slide, kicker, title) {
    slide.addText(kicker, { x: 0.7, y: 0.45, w: 10, h: 0.35, fontFace: KFONT, fontSize: 13, bold: true, color: TEAL, charSpacing: 2 });
    slide.addText(title, { x: 0.7, y: 0.78, w: 12, h: 0.7, fontFace: KFONT, fontSize: 30, bold: true, color: NAVY, margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.72, y: 1.55, w: 0.55, h: 0.07, fill: { color: BLUE } });
  }

  // ========== 슬라이드 1: 타이틀 ==========
  {
    const s = pres.addSlide();
    s.background = { color: NAVY };
    // 배경 장식 원
    s.addShape(pres.shapes.OVAL, { x: 9.8, y: -2.2, w: 6.5, h: 6.5, fill: { color: NAVY2 } });
    s.addShape(pres.shapes.OVAL, { x: 11.3, y: 3.6, w: 4.2, h: 4.2, fill: { color: BLUE, transparency: 70 } });

    iconCircle(s, ic.wheel, 0.9, 0.85, 1.0, BLUE);
    s.addText("배리어프리 대중교통 안내", { x: 2.05, y: 1.02, w: 7, h: 0.6, fontFace: KFONT, fontSize: 15, color: TEAL, bold: true, valign: "middle" });

    s.addText("툭 타", { x: 0.85, y: 2.55, w: 9, h: 1.5, fontFace: KFONT, fontSize: 80, bold: true, color: WHITE, margin: 0 });
    s.addText("Took-Tah", { x: 0.9, y: 3.95, w: 9, h: 0.7, fontFace: "Arial", fontSize: 24, color: TEAL, charSpacing: 3 });

    s.addText("교통약자를 위한 한 번의 터치, 안심 이동", {
      x: 0.9, y: 4.85, w: 11, h: 0.6, fontFace: KFONT, fontSize: 22, color: "CADCFC",
    });
    s.addText("휠체어  ·  유모차  ·  고령자  ·  시각장애인", {
      x: 0.9, y: 5.45, w: 11, h: 0.5, fontFace: KFONT, fontSize: 16, color: "8FA9C4",
    });

    s.addShape(pres.shapes.LINE, { x: 0.9, y: 6.45, w: 4.0, h: 0, line: { color: "31506F", width: 1 } });
    s.addText("Streamlit · Python 기반 발표용 프로토타입", { x: 0.9, y: 6.55, w: 9, h: 0.4, fontFace: KFONT, fontSize: 13, color: "7790AC" });
  }

  // ========== 슬라이드 2: 배경 & 문제 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "WHY  ·  배경", "이동의 정보는 흩어져 있습니다");

    const probs = [
      [ic.bus, "저상버스 정보 단절", "어느 버스가 저상인지, 지금 오는지 한눈에 알기 어렵다"],
      [ic.subway, "역사 시설 접근성", "엘리베이터·리프트 위치, 환승 경로 정보가 분산되어 있다"],
      [ic.door, "출구 선택의 혼란", "수십 개 출구 중 어디로 나가야 목적지에 가까운지 모른다"],
      [ic.exchange, "복잡한 환승", "어디서 갈아타고 얼마나 걷는지 직관적이지 않다"],
    ];
    const cardW = 2.92, gap = 0.28, startX = 0.7, cy = 2.1, cardH = 4.6;
    probs.forEach((p, i) => {
      const x = startX + i * (cardW + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cardW, h: cardH, fill: { color: CARD }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cardW, h: 0.12, fill: { color: BLUE } });
      iconCircle(s, p[0], x + 0.35, cy + 0.5, 1.0, NAVY);
      s.addText(String(i + 1).padStart(2, "0"), { x: x + cardW - 1.0, y: cy + 0.45, w: 0.8, h: 0.6, fontFace: "Arial", fontSize: 30, bold: true, color: "DCE6F0", align: "right" });
      s.addText(p[1], { x: x + 0.3, y: cy + 1.85, w: cardW - 0.6, h: 0.8, fontFace: KFONT, fontSize: 17, bold: true, color: NAVY });
      s.addText(p[2], { x: x + 0.3, y: cy + 2.65, w: cardW - 0.55, h: 1.6, fontFace: KFONT, fontSize: 13, color: GRAY, lineSpacingMultiple: 1.15 });
    });
  }

  // ========== 슬라이드 3: 솔루션 개요 ==========
  {
    const s = pres.addSlide();
    s.background = { color: NAVY };
    s.addShape(pres.shapes.OVAL, { x: -2.0, y: 4.2, w: 6.0, h: 6.0, fill: { color: NAVY2 } });

    s.addText("SOLUTION  ·  한눈에", { x: 0.7, y: 0.55, w: 10, h: 0.35, fontFace: KFONT, fontSize: 13, bold: true, color: TEAL, charSpacing: 2 });
    s.addText("출발지·목적지만 입력하면, 이동 전 과정을 한 화면에", {
      x: 0.7, y: 0.95, w: 12, h: 0.9, fontFace: KFONT, fontSize: 28, bold: true, color: WHITE, margin: 0,
    });

    const items = [
      [ic.route, "맞춤 경로 3종", "빠른 길 · 휠체어 맞춤 · 덜 걷는 길"],
      [ic.bus, "저상버스 실시간", "3단계 판별로 저상 여부 확인"],
      [ic.subway, "지하철 도착·막차", "방면 필터 + 막차 안내"],
      [ic.access, "역사 교통약자 시설", "엘리베이터·리프트·이동 동선"],
      [ic.robot, "AI 음성 브리핑", "도면 분석 + TTS 읽어주기"],
      [ic.loc, "GPS 실시간 위치", "현재 위치 자동 추적 안내"],
    ];
    const cw = 3.9, ch = 1.55, gx = 0.3, gy = 0.3, sx = 0.7, sy = 2.15;
    items.forEach((it, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = sx + col * (cw + gx), y = sy + row * (ch + gy);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: NAVY2 }, line: { color: "2A4D6E", width: 1 } });
      iconCircle(s, it[0], x + 0.28, y + 0.32, 0.9, BLUE);
      s.addText(it[1], { x: x + 1.35, y: y + 0.28, w: cw - 1.5, h: 0.5, fontFace: KFONT, fontSize: 16, bold: true, color: WHITE, margin: 0, valign: "middle" });
      s.addText(it[2], { x: x + 1.35, y: y + 0.78, w: cw - 1.5, h: 0.6, fontFace: KFONT, fontSize: 12, color: "AFC4DA", margin: 0 });
    });
  }

  // ========== 슬라이드 3.5: 앱 미리보기 (실제 화면) ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "PREVIEW  ·  앱 미리보기", "실제 동작 화면");

    const shots = [
      ["presentation/screens/01_home.png", "홈 · 자주 가는 곳", "한 번의 터치로 출발"],
      ["presentation/screens/02_routes.png", "경로 탐색", "모드별 추천 + 저상버스 도착"],
      ["presentation/screens/03_detail.png", "경로 상세", "지도 · 단계 안내 · 시설"],
    ];
    // 폰 목업: 화면비 880:1900 = 0.4632
    const imgH = 4.05, imgW = imgH * (880 / 1900); // ≈ 1.876
    const bez = 0.12;
    const phoneW = imgW + bez * 2;
    const totalW = phoneW * 3 + 1.0 * 2; // 갭 1.0
    const startX = (W - totalW) / 2;
    const topY = 1.95;
    shots.forEach((sh, i) => {
      const px = startX + i * (phoneW + 1.0);
      // 베젤
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px, y: topY, w: phoneW, h: imgH + bez * 2, fill: { color: NAVY }, rectRadius: 0.16, shadow: makeShadow() });
      // 스크린샷
      s.addImage({ path: sh[0], x: px + bez, y: topY + bez, w: imgW, h: imgH });
      // 캡션
      const cy = topY + imgH + bez * 2 + 0.18;
      s.addText(sh[1], { x: px - 0.5, y: cy, w: phoneW + 1.0, h: 0.4, fontFace: KFONT, fontSize: 15, bold: true, color: NAVY, align: "center", margin: 0 });
      s.addText(sh[2], { x: px - 0.5, y: cy + 0.4, w: phoneW + 1.0, h: 0.35, fontFace: KFONT, fontSize: 11.5, color: GRAY, align: "center", margin: 0 });
    });
  }

  // ========== 슬라이드 4: 개발 스택 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "TECH STACK  ·  개발 스택", "검증된 오픈소스 + 공공·외부 API");

    const groups = [
      [ic.python, "언어 · 프레임워크", BLUE, ["Python 3.11", "Streamlit (멀티페이지 UI)", "FastAPI (services HTTP 노출)"]],
      [ic.layer, "지도 · 프론트", TEAL, ["Kakao Maps SDK (위성/하이브리드)", "streamlit-searchbox (자동완성)", "streamlit-js-eval (GPS)"]],
      [ic.db, "공공 데이터 API", NAVY, ["경기 GBIS (버스 도착/위치)", "국토부 TAGO (전국 버스)", "KRIC 레일포털 (운행시각표·시설)"]],
      [ic.brain, "외부 · AI", "7A4FB5", ["ODsay (대중교통 경로)", "Tmap (계단 회피 보행)", "Google Gemini Vision (도면 분석)"]],
    ];
    const cardW = 5.85, cardH = 2.35, gx = 0.35, gy = 0.32, sx = 0.7, sy = 1.95;
    groups.forEach((g, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = sx + col * (cardW + gx), y = sy + row * (cardH + gy);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cardW, h: cardH, fill: { color: CARD }, shadow: makeShadow() });
      iconCircle(s, g[0], x + 0.32, y + 0.35, 0.95, g[2]);
      s.addText(g[1], { x: x + 1.45, y: y + 0.42, w: cardW - 1.6, h: 0.7, fontFace: KFONT, fontSize: 18, bold: true, color: NAVY, valign: "middle", margin: 0 });
      const bullets = g[3].map((t, k) => ({ text: t, options: { bullet: { code: "2022", indent: 14 }, breakLine: true, color: DARKTXT, fontSize: 13 } }));
      s.addText(bullets, { x: x + 0.4, y: y + 1.25, w: cardW - 0.7, h: 1.0, fontFace: KFONT, paraSpaceAfter: 4 });
    });
  }

  // ========== 슬라이드 5: 앱의 주요 요소 (3 모드) ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "FEATURES  ·  앱의 요소", "상황에 맞춘 3가지 경로 모드");

    const modes = [
      [ic.bolt, "빠른 길", BLUE, "최단 시간 우선", ["버스 도착 임박 경로 우선", "총 소요시간 기준 정렬"]],
      [ic.wheel, "휠체어 맞춤", TEAL, "배리어프리 우선", ["저상버스 확정 경로 최상단", "계단 회피·엘리베이터 동선"]],
      [ic.route, "덜 걷는 길", NAVY, "보행 최소화", ["도보 거리 최소 경로", "환승 적은 순으로 정렬"]],
    ];
    const cardW = 3.92, gap = 0.3, sx = 0.7, cy = 1.95, cardH = 3.0;
    modes.forEach((m, i) => {
      const x = sx + i * (cardW + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cardW, h: cardH, fill: { color: CARD }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: 0.13, h: cardH, fill: { color: m[2] } });
      iconCircle(s, m[0], x + 0.38, cy + 0.38, 1.0, m[2]);
      s.addText(m[1], { x: x + 1.5, y: cy + 0.42, w: cardW - 1.6, h: 0.5, fontFace: KFONT, fontSize: 20, bold: true, color: NAVY, margin: 0, valign: "middle" });
      s.addText(m[3], { x: x + 1.5, y: cy + 0.95, w: cardW - 1.6, h: 0.4, fontFace: KFONT, fontSize: 13, color: m[2], bold: true, margin: 0 });
      const b = m[4].map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: true, color: GRAY, fontSize: 12.5 } }));
      s.addText(b, { x: x + 0.4, y: cy + 1.7, w: cardW - 0.7, h: 1.1, fontFace: KFONT, paraSpaceAfter: 5 });
    });

    // 하단 부가 기능 바
    const extras = "자주 가는 곳  ·  최근 검색  ·  현재 위치 GPS  ·  출발/도착 자동완성";
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 5.2, w: 11.9, h: 1.55, fill: { color: NAVY } });
    s.addText("그 외 편의 기능", { x: 1.0, y: 5.42, w: 5, h: 0.4, fontFace: KFONT, fontSize: 13, bold: true, color: TEAL });
    s.addText(extras, { x: 1.0, y: 5.85, w: 11.3, h: 0.7, fontFace: KFONT, fontSize: 17, bold: true, color: WHITE });
  }

  // ========== 슬라이드 6: 핵심 기능 ① 실시간 교통정보 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "CORE ①  ·  실시간 교통정보", "탑승 전에 미리 확인하는 도착·저상 정보");

    // 좌: 저상버스
    const lx = 0.7, ly = 1.95, lw = 5.85, lh = 4.7;
    s.addShape(pres.shapes.RECTANGLE, { x: lx, y: ly, w: lw, h: lh, fill: { color: CARD }, shadow: makeShadow() });
    iconCircle(s, ic.bus, lx + 0.35, ly + 0.35, 0.95, BLUE);
    s.addText("저상버스 실시간 도착", { x: lx + 1.45, y: ly + 0.45, w: lw - 1.6, h: 0.6, fontFace: KFONT, fontSize: 19, bold: true, color: NAVY, valign: "middle", margin: 0 });
    const busSteps = [
      ["1단계", "lowPlate 필드", "도착 API의 저상 플래그 직접 확인"],
      ["2단계", "차량 위치 조회", "운행 중 차량의 저상 여부 교차 확인"],
      ["3단계", "노선 키워드", "노선 정보의 저상 운행 여부 확인"],
    ];
    busSteps.forEach((b, i) => {
      const y = ly + 1.55 + i * 1.0;
      s.addShape(pres.shapes.RECTANGLE, { x: lx + 0.35, y, w: 1.05, h: 0.7, fill: { color: TEAL } });
      s.addText(b[0], { x: lx + 0.35, y, w: 1.05, h: 0.7, fontFace: KFONT, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
      s.addText(b[1], { x: lx + 1.55, y: y - 0.02, w: lw - 1.8, h: 0.4, fontFace: KFONT, fontSize: 15, bold: true, color: DARKTXT, margin: 0 });
      s.addText(b[2], { x: lx + 1.55, y: y + 0.36, w: lw - 1.8, h: 0.4, fontFace: KFONT, fontSize: 12, color: GRAY, margin: 0 });
    });

    // 우: 지하철
    const rx = 6.75, ry = 1.95, rw = 5.85, rh = 4.7;
    s.addShape(pres.shapes.RECTANGLE, { x: rx, y: ry, w: rw, h: rh, fill: { color: NAVY }, shadow: makeShadow() });
    iconCircle(s, ic.subway, rx + 0.35, ry + 0.35, 0.95, BLUE);
    s.addText("지하철 도착시간 · 막차", { x: rx + 1.45, y: ry + 0.45, w: rw - 1.6, h: 0.6, fontFace: KFONT, fontSize: 19, bold: true, color: WHITE, valign: "middle", margin: 0 });
    const subFeat = [
      ["방면 필터링", "내가 가는 방향 열차만 선별해 표시"],
      ["막차 안내", "막차 통과 시 'after_last' 상태로 안내"],
      ["KRIC 운행시각표", "역사별 시간표 기반, 분 단위 로컬 재계산"],
      ["인접역 방면 표기", "(종점, 인접역) 방면 — 실제 표지판과 동일"],
    ];
    subFeat.forEach((f, i) => {
      const y = ry + 1.55 + i * 0.78;
      s.addImage({ data: ic.check, x: rx + 0.4, y: y + 0.05, w: 0.3, h: 0.3 });
      s.addText(f[0], { x: rx + 0.85, y, w: rw - 1.1, h: 0.38, fontFace: KFONT, fontSize: 15, bold: true, color: WHITE, margin: 0 });
      s.addText(f[1], { x: rx + 0.85, y: y + 0.36, w: rw - 1.1, h: 0.38, fontFace: KFONT, fontSize: 12, color: "AFC4DA", margin: 0 });
    });
  }

  // ========== 슬라이드 7: 핵심 기능 ② 접근성 & AI ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "CORE ②  ·  접근성 & AI", "역 안에서의 이동까지 책임지는 안내");

    const feats = [
      [ic.access, "역사 교통약자 시설", BLUE, ["KRIC 엘리베이터·리프트 위치", "역내 이동 동선 + 환승 이동 정보", "노선 인지 역코드 매칭"]],
      [ic.door, "출구 자동 판별", TEAL, ["정류장과 가장 가까운 출구 추천", "Tier1 정규식 + Tier2 GPS 최근접", "AI 브리핑·시설 탭 동기화"]],
      [ic.robot, "AI 브리핑 + TTS", "7A4FB5", ["Gemini Vision 역사 도면 분석", "휠체어 관점 4~5문장 안내", "음성으로 읽어주기 (Web Speech)"]],
    ];
    const cw = 3.92, gap = 0.3, sx = 0.7, cy = 1.95, ch = 4.6;
    feats.forEach((f, i) => {
      const x = sx + i * (cw + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cw, h: ch, fill: { color: CARD }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cw, h: 0.12, fill: { color: f[2] } });
      iconCircle(s, f[0], x + 0.35, cy + 0.45, 1.05, f[2]);
      s.addText(f[1], { x: x + 0.3, y: cy + 1.75, w: cw - 0.6, h: 0.8, fontFace: KFONT, fontSize: 17, bold: true, color: NAVY });
      const b = f[3].map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: true, color: DARKTXT, fontSize: 13 } }));
      s.addText(b, { x: x + 0.35, y: cy + 2.6, w: cw - 0.65, h: 1.8, fontFace: KFONT, paraSpaceAfter: 7, lineSpacingMultiple: 1.05 });
    });
  }

  // ========== 슬라이드 8: 구현 방식 ① 알고리즘 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "HOW ①  ·  핵심 알고리즘", "정확도를 끌어올린 판별 로직");

    const rows = [
      [ic.bus, "저상버스 3단계 폴백", "lowPlate → 차량 위치 → 노선 키워드 순으로 단계적 확인. 한 단계가 비어도 다음 단계로 보완해 누락을 최소화."],
      [ic.door, "출구 ↔ 정류장 거리 매칭", "역의 모든 출구 좌표를 카카오로 병렬 수집한 뒤, 버스 정류장과 최단 거리 출구를 추천. 정규식(Tier1) 우선, 없으면 GPS 최근접(Tier2)."],
      [ic.exchange, "노선 인지 환승역 처리", "동명 환승역은 노선명을 정규화해 정확한 역코드 선택. 예) 이매역 — 경강선 K411 vs 수인분당선 '이매(성남아트센터)' K227 구분."],
    ];
    const sx = 0.7, sy = 1.95, rw = 11.9, rh = 1.45, gy = 0.18;
    rows.forEach((r, i) => {
      const y = sy + i * (rh + gy);
      s.addShape(pres.shapes.RECTANGLE, { x: sx, y, w: rw, h: rh, fill: { color: CARD }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x: sx, y, w: 0.13, h: rh, fill: { color: BLUE } });
      iconCircle(s, r[0], sx + 0.4, y + 0.32, 0.82, NAVY);
      s.addText(r[1], { x: sx + 1.6, y: y + 0.2, w: rw - 1.9, h: 0.45, fontFace: KFONT, fontSize: 17, bold: true, color: NAVY, margin: 0 });
      s.addText(r[2], { x: sx + 1.6, y: y + 0.68, w: rw - 1.9, h: 0.7, fontFace: KFONT, fontSize: 13, color: GRAY, margin: 0, lineSpacingMultiple: 1.1 });
    });
  }

  // ========== 슬라이드 9: 구현 방식 ② 최적화 ==========
  {
    const s = pres.addSlide();
    s.background = { color: NAVY };
    s.addShape(pres.shapes.OVAL, { x: 10.2, y: 4.0, w: 5.5, h: 5.5, fill: { color: NAVY2 } });
    s.addText("HOW ②  ·  성능 최적화", { x: 0.7, y: 0.55, w: 10, h: 0.35, fontFace: KFONT, fontSize: 13, bold: true, color: TEAL, charSpacing: 2 });
    s.addText("빠른 화면, 그리고 API 한도 관리", { x: 0.7, y: 0.95, w: 12, h: 0.7, fontFace: KFONT, fontSize: 28, bold: true, color: WHITE, margin: 0 });

    const cards = [
      [ic.bolt, "병렬 호출", "ThreadPoolExecutor로 여러 정류장·역의 API를 동시에 호출. 출구 좌표 수집 약 3~6초 → 0.7초로 단축."],
      [ic.clock, "시간 버킷 캐시", "정적인 지하철 시간표는 5분 캐시 후 분 단위만 로컬 재계산. 버스 도착은 60초 버킷으로 호출량 절감."],
      [ic.cogs, "3단계 보행 파이프라인", "Tmap 보행 경로를 좌표 계산 → 미캐시분 병렬 호출 → 조립 단계로 분리해 중복 호출 제거."],
      [ic.db, "API 한도 보호", "카카오 지역 판별 호출 제거(GBIS 우선→TAGO 폴백), lru_cache·session_state 캐시로 중복 요청 차단."],
    ];
    const cw = 5.85, ch = 2.15, gx = 0.35, gy = 0.32, sx = 0.7, sy = 2.0;
    cards.forEach((c, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = sx + col * (cw + gx), y = sy + row * (ch + gy);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: NAVY2 } });
      iconCircle(s, c[0], x + 0.3, y + 0.32, 0.85, BLUE);
      s.addText(c[1], { x: x + 1.3, y: y + 0.3, w: cw - 1.5, h: 0.5, fontFace: KFONT, fontSize: 17, bold: true, color: WHITE, margin: 0, valign: "middle" });
      s.addText(c[2], { x: x + 0.35, y: y + 1.1, w: cw - 0.65, h: 0.95, fontFace: KFONT, fontSize: 12.5, color: "AFC4DA", margin: 0, lineSpacingMultiple: 1.12 });
    });
  }

  // ========== 슬라이드 10: 시스템 아키텍처 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "ARCHITECTURE  ·  시스템 구성", "UI · 서비스 · 외부 API의 3계층 구조");

    const colY = 2.2, colH = 4.0;
    const cols = [
      ["사용자 / UI", BLUE, ["Streamlit 멀티페이지", "홈 · 경로탐색 · 경로상세 · 설정", "Kakao Maps SDK 지도"]],
      ["서비스 계층 (services/)", NAVY, ["geocode · kakao_local", "odsay · tmap · bus_arrival", "rail_portal · subway_arrival", "ai_briefing"]],
      ["외부 · 공공 API", TEAL, ["GBIS · TAGO · KRIC", "ODsay · Tmap · Kakao", "Google Gemini"]],
    ];
    const cw = 3.6, gap = 0.62, sx = 0.85;
    cols.forEach((c, i) => {
      const x = sx + i * (cw + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: colY, w: cw, h: 0.7, fill: { color: c[1] } });
      s.addText(c[0], { x, y: colY, w: cw, h: 0.7, fontFace: KFONT, fontSize: 15, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
      s.addShape(pres.shapes.RECTANGLE, { x, y: colY + 0.7, w: cw, h: colH - 0.7, fill: { color: CARD }, shadow: makeShadow() });
      const b = c[2].map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: true, color: DARKTXT, fontSize: 13.5 } }));
      s.addText(b, { x: x + 0.35, y: colY + 1.0, w: cw - 0.6, h: colH - 1.2, fontFace: KFONT, paraSpaceAfter: 8 });
      // 화살표
      if (i < 2) {
        s.addText("→", { x: x + cw + 0.02, y: colY + 1.3, w: gap, h: 0.7, fontFace: "Arial", fontSize: 30, bold: true, color: GRAY, align: "center" });
      }
    });

    // FastAPI 병행 노트
    s.addShape(pres.shapes.RECTANGLE, { x: 0.85, y: 6.45, w: 11.6, h: 0.62, fill: { color: NAVY } });
    s.addText([
      { text: "FastAPI 백엔드 병행  ", options: { bold: true, color: TEAL, fontSize: 13 } },
      { text: "— services 함수를 HTTP로 노출해 향후 React 마이그레이션 대비", options: { color: "CADCFC", fontSize: 13 } },
    ], { x: 1.1, y: 6.45, w: 11.1, h: 0.62, fontFace: KFONT, valign: "middle", margin: 0 });
  }

  // ========== 슬라이드 11: 접근성 설계 원칙 ==========
  {
    const s = pres.addSlide();
    s.background = { color: LIGHT };
    lightHeader(s, "PRINCIPLES  ·  접근성 설계", "교통약자를 최우선에 둔 UI 원칙");

    const items = [
      [ic.access, "큰 터치 영역", "모든 버튼 최소 48×48dp, 본문 18px 이상"],
      [ic.eye, "고대비 색상", "메인 컬러 #1F77B4, 명확한 명암 대비"],
      [ic.mobile, "모바일 세로 최적화", "1080×1920 기준, 한 손 조작 동선"],
      [ic.loc, "GPS 상시 적용", "앱 실행 시 현재 위치 자동 인식·지도 표시"],
      [ic.mic, "음성 안내", "AI 브리핑 TTS로 듣기 지원"],
      [ic.handsHelping, "안심 동선", "계단 회피·엘리베이터 우선 경로 제공"],
    ];
    const cw = 3.85, ch = 1.95, gx = 0.3, gy = 0.3, sx = 0.7, sy = 1.95;
    items.forEach((it, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = sx + col * (cw + gx), y = sy + row * (ch + gy);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: CARD }, shadow: makeShadow() });
      iconCircle(s, it[0], x + 0.32, y + 0.32, 0.9, i % 2 === 0 ? BLUE : TEAL);
      s.addText(it[1], { x: x + 1.35, y: y + 0.32, w: cw - 1.5, h: 0.55, fontFace: KFONT, fontSize: 16, bold: true, color: NAVY, margin: 0, valign: "middle" });
      s.addText(it[2], { x: x + 0.32, y: y + 1.25, w: cw - 0.6, h: 0.6, fontFace: KFONT, fontSize: 12.5, color: GRAY, margin: 0, lineSpacingMultiple: 1.1 });
    });
  }

  // ========== 슬라이드 12: 기타 & 향후 + 마무리 ==========
  {
    const s = pres.addSlide();
    s.background = { color: NAVY };
    s.addShape(pres.shapes.OVAL, { x: 9.5, y: -2.5, w: 7.0, h: 7.0, fill: { color: NAVY2 } });
    s.addShape(pres.shapes.OVAL, { x: 11.5, y: 4.0, w: 4.0, h: 4.0, fill: { color: BLUE, transparency: 75 } });

    s.addText("WRAP-UP  ·  기타 & 향후", { x: 0.7, y: 0.55, w: 10, h: 0.35, fontFace: KFONT, fontSize: 13, bold: true, color: TEAL, charSpacing: 2 });
    s.addText("지금도 동작하고, 더 확장됩니다", { x: 0.7, y: 0.95, w: 12, h: 0.7, fontFace: KFONT, fontSize: 28, bold: true, color: WHITE, margin: 0 });

    const left = [
      ["배포", "Streamlit Community Cloud (tooktar.streamlit.app)"],
      ["보안", ".env 분리 / st.secrets, API 키 비커밋 원칙"],
      ["폴백", "API 실패 시 더미 데이터로 시연 안정성 확보"],
    ];
    const right = [
      ["지하철 실시간 확대", "국가철도공단 API 승인 시 실시간 도착 강화"],
      ["React 마이그레이션", "FastAPI 백엔드 기반으로 점진적 전환"],
      ["전국 커버리지", "TAGO 도시코드 확장으로 비수도권 강화"],
    ];
    function block(title, data, x) {
      s.addText(title, { x, y: 2.05, w: 5.6, h: 0.45, fontFace: KFONT, fontSize: 15, bold: true, color: TEAL });
      data.forEach((d, i) => {
        const y = 2.65 + i * 1.05;
        s.addImage({ data: ic.check, x, y: y + 0.04, w: 0.32, h: 0.32 });
        s.addText(d[0], { x: x + 0.5, y, w: 5.1, h: 0.4, fontFace: KFONT, fontSize: 15, bold: true, color: WHITE, margin: 0 });
        s.addText(d[1], { x: x + 0.5, y: y + 0.38, w: 5.1, h: 0.55, fontFace: KFONT, fontSize: 12.5, color: "AFC4DA", margin: 0, lineSpacingMultiple: 1.1 });
      });
    }
    block("현재 상태", left, 0.7);
    block("향후 계획", right, 6.9);

    s.addShape(pres.shapes.LINE, { x: 0.7, y: 6.35, w: 11.9, h: 0, line: { color: "31506F", width: 1 } });
    s.addText("툭 타 — 한 번의 터치로, 누구에게나 열린 이동", { x: 0.7, y: 6.5, w: 11.9, h: 0.6, fontFace: KFONT, fontSize: 18, bold: true, color: WHITE, align: "center" });
  }

  await pres.writeFile({ fileName: "presentation/툭타_앱소개.pptx" });
  console.log("DONE");
}

main().catch((e) => { console.error(e); process.exit(1); });
