/** 툭 타 디자인 토큰 — Streamlit components/styles.py 의 네이비 테마 이식 */

export const colors = {
  navy: '#1F3A5E',
  navy2: '#143A5E',
  blue: '#1F77B4',
  primary: '#1f77b4',
  teal: '#2EC4B6',
  light: '#F4F7FB',
  card: '#FFFFFF',
  gray: '#5B6B7B',
  grayLight: '#8A98A6',
  darkText: '#1B2733',
  bg: '#EEF2F6',
  danger: '#D9534F',
  lowFloor: '#002F6C',
  border: '#E2E8F0',
};

/** 접근성 원칙: 최소 글자 18px, 터치 영역 48dp */
export const sizes = {
  minTouch: 48,
  fontBody: 18,
  fontSmall: 15,
  fontTitle: 26,
  fontLogo: 55,
  radius: 16,
  radiusSm: 12,
  gap: 12,
};

export const font = {
  // 시스템 기본 — 추후 Gowun Batang 등 커스텀 폰트 로드 가능
  serifWeight: '700' as const,
};
