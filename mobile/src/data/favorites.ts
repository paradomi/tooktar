/** 자주 가는 곳 — data/dummy_data.py 의 FAVORITE_PLACES 이식 */

export interface FavoritePlace {
  icon: string;
  label: string;
  address: string;
  lng: number;
  lat: number;
}

// 기본값은 모든 방문자에게 동일하게 보이므로 개인 주소 금지 — 공공장소 예시만.
// 사용자가 편집하면 그때부터 본인 기기(localStorage/AsyncStorage)에만 저장됨.
export const FAVORITE_PLACES: FavoritePlace[] = [
  { icon: '🚉', label: '수원역', address: '경기 수원시 팔달구 매산로1가', lng: 127.000094700292, lat: 37.2657903079673 },
  { icon: '🏥', label: '병원', address: '아주대학교병원', lng: 127.04751881022693, lat: 37.27943874786612 },
  { icon: '🛒', label: '시장', address: '못골종합시장', lng: 127.02126744710107, lat: 37.27546918387394 },
  { icon: '🏛️', label: '시청', address: '수원시청', lng: 127.028715898311, lat: 37.263584678785 },
];

/** 출발지 기본값 — CLAUDE.md: 현재 위치(수원시 영통구) */
export const DEFAULT_ORIGIN = {
  name: '현재 위치 (수원시 영통구)',
  address: '경기도 수원시 영통구',
  lng: 127.0467,
  lat: 37.2411,
};
