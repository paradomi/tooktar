/** 경로 모드 — pages/1_경로_탐색.py 의 모드 카드 이식 */

export interface RouteMode {
  key: 'fast' | 'wheel' | 'walk_less';
  icon: string;
  name: string;
  sub: string;
  desc: string;
  searchType: number; // ODsay search_type (0=최단시간, 1=최소환승)
}

export const ROUTE_MODES: RouteMode[] = [
  {
    key: 'fast',
    icon: '⚡',
    name: '빠른 길',
    sub: '최단 시간',
    desc: '가장 빨리 도착하는 경로',
    searchType: 0,
  },
  {
    key: 'wheel',
    icon: '♿',
    name: '휠체어 맞춤',
    sub: '단차 없음',
    desc: '저상버스 우선, 계단 제외 보행, 엘리베이터 출구 안내',
    searchType: 0,
  },
  {
    key: 'walk_less',
    icon: '🚶',
    name: '덜 걷는 길',
    sub: '도보 최소',
    desc: '환승과 도보가 적은 경로',
    searchType: 1,
  },
];
