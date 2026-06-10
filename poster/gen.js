/** 툭타 앱 소개 A1 포스터 (초안) — pptxgenjs */
const pptxgen = require('pptxgenjs');
const p = new pptxgen();

// A1 세로 (594 x 841 mm = 23.39 x 33.11 in)
const W = 23.39, H = 33.11;
p.defineLayout({ name: 'A1', width: W, height: H });
p.layout = 'A1';

// 앱 테마 색
const NAVY = '002F6C';
const BLUE = '1F77B4';
const SKY = 'D6E6F5';
const BG = 'EAF3FC';
const INK = '233140';
const GRAY = '5A6B7B';
const GREEN = '2DB400';
const RED = 'D32F2F';
const YEL = 'F5B400';
const WHITE = 'FFFFFF';
const FONT = 'Gowun Batang';      // 앱과 동일 (없으면 PowerPoint가 serif로 대체)
const FONT_B = 'Gowun Batang';

const slide = p.addSlide();
slide.background = { color: BG };

// ── 외곽 라운드 테두리
slide.addShape('roundRect', {
  x: 0.25, y: 0.25, w: W - 0.5, h: H - 0.5,
  fill: { type: 'solid', color: WHITE }, line: { color: SKY, width: 3 }, rectRadius: 0.4,
});

// ───────────────────────── 헤더
const HX = 0.6, HY = 0.55, HW = W - 1.2, HH = 3.15;
slide.addShape('roundRect', {
  x: HX, y: HY, w: HW, h: HH,
  fill: { color: NAVY }, line: { type: 'none' }, rectRadius: 0.35,
});
// 돋보기 아이콘 (원 + 손잡이)
slide.addShape('oval', {
  x: HX + 0.6, y: HY + 0.75, w: 1.5, h: 1.5,
  fill: { type: 'none' }, line: { color: 'FFD23F', width: 8 },
});
slide.addShape('roundRect', {
  x: HX + 1.85, y: HY + 2.0, w: 0.85, h: 0.28, rotate: 45,
  fill: { color: 'FFD23F' }, line: { type: 'none' }, rectRadius: 0.14,
});
// 헤더 텍스트
slide.addText(
  [
    { text: '이동의 장벽을 툭, 넘다', options: { fontSize: 60, bold: true, color: WHITE, breakLine: true } },
    { text: ': 교통약자 전용 배리어프리 대중교통 안내 앱  「툭 타」', options: { fontSize: 30, color: 'CFE3F7' } },
  ],
  { x: HX + 2.9, y: HY + 0.3, w: HW - 3.4, h: HH - 0.6, align: 'left', valign: 'middle', fontFace: FONT_B, lineSpacingMultiple: 1.05 }
);

// ───────────────────────── 레이아웃 좌표 (3열)
const M = 0.6;
const top = HY + HH + 0.45;          // 본문 시작 y
const colGap = 0.45;
const colW = (W - 2 * M - 2 * colGap) / 3;
const c1 = M, c2 = M + colW + colGap, c3 = M + 2 * (colW + colGap);
const footH = 1.15;
const bodyBottom = H - 0.6 - footH - 0.3;
const bodyH = bodyBottom - top;

// ── 섹션 그리기 헬퍼
function section(x, y, w, h, num, title, accent, lines, opts = {}) {
  // 카드
  slide.addShape('roundRect', {
    x, y, w, h, fill: { color: WHITE }, line: { color: SKY, width: 2.5 }, rectRadius: 0.28,
    shadow: { type: 'outer', color: 'B9CBDD', blur: 6, offset: 3, angle: 90, opacity: 0.5 },
  });
  // 번호 배지
  const bs = 1.25;
  slide.addShape('roundRect', {
    x: x + 0.35, y: y + 0.32, w: bs, h: bs,
    fill: { color: accent }, line: { type: 'none' }, rectRadius: 0.22,
  });
  slide.addText(String(num), {
    x: x + 0.35, y: y + 0.32, w: bs, h: bs, align: 'center', valign: 'middle',
    fontSize: 46, bold: true, color: WHITE, fontFace: FONT_B,
  });
  // 제목
  slide.addText(title, {
    x: x + 0.35 + bs + 0.3, y: y + 0.32, w: w - bs - 1.1, h: bs, align: 'left', valign: 'middle',
    fontSize: opts.titleSize || 27, bold: true, color: NAVY, fontFace: FONT_B,
  });
  // 구분선
  slide.addShape('line', {
    x: x + 0.4, y: y + 0.32 + bs + 0.18, w: w - 0.8, h: 0,
    line: { color: SKY, width: 2 },
  });
  // 본문
  const bodyY = y + 0.32 + bs + 0.42;
  slide.addText(
    lines.map((l) => ({
      text: l.t,
      options: {
        bullet: l.b === false ? false : { code: '2022', indent: 14 },
        fontSize: l.s || opts.bodySize || 17,
        bold: !!l.bold,
        color: l.c || INK,
        breakLine: true,
        paraSpaceAfter: l.gap || 7,
        indentLevel: l.lvl || 0,
      },
    })),
    { x: x + 0.45, y: bodyY, w: w - 0.9, h: h - (bodyY - y) - 0.3, align: 'left', valign: 'top', fontFace: FONT, lineSpacingMultiple: 1.02 }
  );
}

// ── 1열: 섹션 1, 2
const s1h = bodyH * 0.40;
const s2h = bodyH - s1h - 0.45;
section(c1, top, colW, s1h, 1, '개발 배경', BLUE, [
  { t: '휠체어·유모차·고령자·시각장애인 등 교통약자는 대중교통 이용 시 큰 장벽에 부딪힌다.', bold: true, c: NAVY },
  { t: '계단, 저상버스 운행 여부, 역내 엘리베이터·경사로 위치 정보를 한 번에 알기 어렵다.' },
  { t: '기존 길찾기 앱은 「최단·최속」에만 초점 → 배리어프리 정보가 부족하다.' },
  { t: '“탈 수 있는 경로”가 필요하다.', bold: true, c: BLUE },
]);
section(c1, top + s1h + 0.45, colW, s2h, 2, '문제 설정 & 목표', '0E7C86', [
  { t: '문제 정의', bold: true, c: NAVY, b: false, s: 19 },
  { t: '저상버스 실제 운행 여부를 알 수 없음' },
  { t: '역내 엘리베이터·리프트·경사로 정보 분산' },
  { t: '계단 없는 도보 경로 안내 부재' },
  { t: '교통약자 맞춤 경로 정렬 기능 없음' },
  { t: '목표', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: '교통약자 관점에서 안전하게 “탈 수 있는” 경로를 한 화면에 안내하는 배리어프리 길찾기 앱', bold: true, c: '0E7C86' },
  { t: '실시간 도착·시설·AI 안내까지 통합', c: GRAY },
]);

// ── 2열: 섹션 3 (핵심 기능, 가장 큼)
section(c2, top, colW, bodyH, 3, '핵심 기능 · 결과물', RED, [
  { t: '저상버스 실시간 3단계 판별', bold: true, c: NAVY, b: false, s: 19 },
  { t: 'GBIS lowPlate → 차량위치 → 노선 키워드 교차검증', lvl: 1 },
  { t: '계단회피 도보 경로', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: 'Tmap 보행 API(계단 제외) + 턴바이턴 + 카카오 거리뷰', lvl: 1 },
  { t: '휠체어 맞춤 경로 우선 정렬', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: '저상버스 친화도 점수화로 추천 경로 재정렬', lvl: 1 },
  { t: '지하철 교통약자 시설 안내', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: 'KRIC 역내 엘리베이터·리프트 도면 + 출구 자동 판별', lvl: 1 },
  { t: 'AI 경로 브리핑', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: 'Gemini Vision이 역 도면을 분석해 이동 동선 안내', lvl: 1 },
  { t: '실시간 안내 모드', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: 'GPS 기반 도보 네비, 정류장 진행 화면, 승·하차 알람', lvl: 1 },
  { t: '저상버스 · 광역 · 마을 · 지하철 색상 구분 지도', bold: true, c: BLUE, b: false, gap: 4, s: 18 },
]);

// ── 3열: 섹션 4, 5
const s4h = bodyH * 0.52;
const s5h = bodyH - s4h - 0.45;
section(c3, top, colW, s4h, 4, '기술 구현 & 타당성', YEL, [
  { t: '구현 스택', bold: true, c: NAVY, b: false, s: 19 },
  { t: 'React Native (Expo) · TypeScript' },
  { t: 'FastAPI 백엔드 (로직 1벌로 웹·앱 공유)' },
  { t: '활용 데이터', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: '경기 GBIS · 국토부 TAGO (버스)' },
  { t: 'KRIC 레일포털 (역 교통약자 시설)' },
  { t: 'ODsay(경로) · Tmap(보행) · Kakao(지도)' },
  { t: 'Google Gemini Vision (AI 도면 분석)' },
  { t: '타당성: 모두 공개 공공·상용 API로 검증 가능', bold: true, c: 'A36A00', b: false, gap: 4, s: 16 },
]);
section(c3, top + s4h + 0.45, colW, s5h, 5, '기대효과 & 느낀점', GREEN, [
  { t: '교통약자의 이동권·자립성 향상', bold: true, c: NAVY },
  { t: '실시간·AI 안내로 외출 부담과 불확실성 감소' },
  { t: '한 앱에서 저상버스·시설·도보까지 통합 확인' },
  { t: '느낀점', bold: true, c: NAVY, b: false, s: 19, gap: 4 },
  { t: '공공데이터의 한계를 교차검증·AI로 보완할 수 있음을 확인' },
  { t: '사용자(교통약자) 관점의 설계가 핵심임을 체감' },
]);

// ───────────────────────── 푸터
const fy = H - 0.6 - footH;
slide.addShape('roundRect', {
  x: M, y: fy, w: W - 2 * M, h: footH,
  fill: { color: NAVY }, line: { type: 'none' }, rectRadius: 0.25,
});
slide.addText(
  [
    { text: '툭 타  ', options: { fontSize: 34, bold: true, color: 'FFD23F' } },
    { text: 'TOOK-TAH', options: { fontSize: 22, color: 'CFE3F7' } },
    { text: '      이동의 장벽을 툭, 넘다 — 교통약자 누구나 닿을 수 있는 길', options: { fontSize: 22, color: WHITE } },
  ],
  { x: M + 0.4, y: fy, w: W - 2 * M - 0.8, h: footH, align: 'left', valign: 'middle', fontFace: FONT_B }
);

p.writeFile({ fileName: 'C:/Users/손지완/Documents/onetouch/poster/툭타_포스터_초안.pptx' }).then((f) =>
  console.log('saved:', f)
);
