/** 자주 가는 곳 — data/dummy_data.py 의 FAVORITE_PLACES 이식 */

export interface FavoritePlace {
  icon: string;
  label: string;
  address: string;
  lng: number;
  lat: number;
}

export const FAVORITE_PLACES: FavoritePlace[] = [
  { icon: '🏠', label: '집', address: '우남1차아파트', lng: 127.03362843525207, lat: 37.247332166005776 },
  { icon: '🏥', label: '병원', address: '아주대학교병원', lng: 127.04751881022693, lat: 37.27943874786612 },
  { icon: '🛒', label: '시장', address: '못골종합시장', lng: 127.02126744710107, lat: 37.27546918387394 },
  { icon: '👨‍👩‍👧', label: '자녀 집', address: '성남시청', lng: 127.12628813511819, lat: 37.41993055742254 },
];

export const RECENT_SEARCHES = [
  { name: '수원시청', address: '경기도 수원시 팔달구 효원로 241' },
  { name: '아주대병원', address: '경기도 수원시 영통구 월드컵로 164' },
  { name: '수원역', address: '경기도 수원시 팔달구 덕영대로 924' },
];

/** 출발지 기본값 — CLAUDE.md: 현재 위치(수원시 영통구) */
export const DEFAULT_ORIGIN = {
  name: '현재 위치 (수원시 영통구)',
  address: '경기도 수원시 영통구',
  lng: 127.0467,
  lat: 37.2411,
};
