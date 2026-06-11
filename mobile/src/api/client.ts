/** 툭 타 백엔드(FastAPI) 클라이언트
 *
 * 백엔드 실행: uvicorn backend.main:app --reload --port 8000
 *
 * BASE_URL 주의:
 *  - 웹/iOS 시뮬레이터: http://localhost:8000
 *  - Android 에뮬레이터: http://10.0.2.2:8000  (에뮬레이터→호스트 매핑)
 *  - 실기기: 같은 와이파이의 PC 내부 IP (예: http://192.168.0.x:8000)
 */
import { Platform } from 'react-native';

const HOST =
  Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

// 웹(Expo Web): 배포 빌드는 https 백엔드(EXPO_PUBLIC_API_URL)를 쓰고,
// 개발 시 .env 의 PC IP(http://192.168...)는 실기기(폰) 전용이므로 웹에서는 무시 → localhost.
// 네이티브(폰/에뮬레이터)는 EXPO_PUBLIC_API_URL(PC 내부 IP) 우선.
const ENV_URL = process.env.EXPO_PUBLIC_API_URL || '';
export const BASE_URL =
  Platform.OS === 'web'
    ? ENV_URL.startsWith('https://')
      ? ENV_URL
      : 'http://localhost:8000'
    : ENV_URL || HOST;

export interface Coord {
  name: string;
  address: string;
  lng: number;
  lat: number;
}

// 백엔드 생존 알림 — 아무 API 든 성공하면 구독자(연결 배너 등)에게 알림
const aliveListeners = new Set<() => void>();
/** 백엔드 응답 성공 시 호출될 콜백 등록. 반환 함수로 해제. */
export function onBackendAlive(cb: () => void): () => void {
  aliveListeners.add(cb);
  return () => {
    aliveListeners.delete(cb);
  };
}
function notifyAlive() {
  aliveListeners.forEach((cb) => cb());
}

async function getJson<T>(path: string, timeoutMs = 8000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE_URL}${path}`, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    notifyAlive();
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

async function postJson<T>(path: string, body: unknown, timeoutMs = 12000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    notifyAlive();
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** 백엔드가 깰 때까지 재시도 헬스 체크 — Render 무료 티어 콜드 스타트(30~50초) 대응.
 *  깨어나면 즉시 true. maxMs 동안 못 깨우면 false. */
export async function waitForBackend(maxMs = 75000): Promise<boolean> {
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    if (await checkHealth(10000)) return true;
    await new Promise((r) => setTimeout(r, 2500));
  }
  return false;
}

/** 백엔드 헬스 체크 */
export async function checkHealth(timeoutMs = 3000): Promise<boolean> {
  try {
    const r = await getJson<{ status: string }>('/health', timeoutMs);
    return r.status === 'ok';
  } catch {
    return false;
  }
}

/** 공개 설정 (카카오맵 JS 키 등) */
let _configCache: { kakao_js_key: string } | null = null;
export async function getConfig(): Promise<{ kakao_js_key: string }> {
  if (_configCache) return _configCache;
  try {
    _configCache = await getJson<{ kakao_js_key: string }>('/config', 4000);
  } catch {
    _configCache = { kakao_js_key: '' };
  }
  return _configCache;
}

/** ODsay loadLane — 경로 실제 주행 폴리라인 (백엔드 /routes/lane) */
export interface LaneData {
  lane?: {
    class?: number;
    section?: { graphPos?: { x: number; y: number }[] }[];
  }[];
}
export async function loadLane(mapObj: string): Promise<LaneData | null> {
  if (!mapObj) return null;
  try {
    return await getJson<LaneData>(`/routes/lane?map_obj=${encodeURIComponent(mapObj)}`, 12000);
  } catch {
    return null;
  }
}

/** Tmap 보행자 경로 — 도보 구간 폴리라인 좌표 (백엔드 /walk/pedestrian) */
export interface WalkReq {
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  search_option?: number; // 0=기본, 4=계단 제외(휠체어)
}
export async function walkRoute(req: WalkReq): Promise<{ lat: number; lng: number }[]> {
  const { coords } = await walkRouteDetail(req);
  return coords;
}

/** 도보 턴바이턴 안내 1개 (Tmap Point feature) */
export interface WalkGuide {
  turn_type: number; // Tmap turnType (11직진/12좌/13우/14유턴/200출발/201도착/211~횡단보도·계단 등)
  description: string; // "○○ 방면으로 횡단보도 건너기"
  distance: number; // 이 지점 이후 이동 거리(m)
  lat: number;
  lng: number;
}

/** Tmap 보행자 경로 — 폴리라인 + 턴바이턴 안내 (백엔드 /walk/pedestrian) */
export async function walkRouteDetail(
  req: WalkReq
): Promise<{ coords: { lat: number; lng: number }[]; guides: WalkGuide[] }> {
  try {
    const r = await postJson<{
      coords: { lat: number; lng: number }[];
      guides: WalkGuide[];
      fallback: boolean;
    }>(
      '/walk/pedestrian',
      { start_name: '출발', end_name: '도착', search_option: 0, ...req },
      12000
    );
    return { coords: r.coords || [], guides: r.guides || [] };
  } catch {
    return { coords: [], guides: [] };
  }
}

/** 주소/장소명 → 좌표 (카카오 REST, 백엔드 /geocode) */
export async function geocode(address: string): Promise<Coord | null> {
  try {
    return await getJson<Coord>(`/geocode?address=${encodeURIComponent(address)}`);
  } catch {
    return null;
  }
}

/** 좌표 → 주소/지명 (백엔드 /reverse-geocode) — GPS 현재위치 표시용 */
export async function coordToAddress(lng: number, lat: number): Promise<Coord | null> {
  try {
    return await getJson<Coord>(`/reverse-geocode?lng=${lng}&lat=${lat}`);
  } catch {
    return null;
  }
}

/** 장소 검색 결과 (자동완성) */
export interface PlaceResult {
  place_name: string;
  address: string;
  lng: number | null;
  lat: number | null;
}

/** 카카오 키워드 검색 — 자동완성 (백엔드 /places) */
export async function searchPlaces(query: string, size = 8): Promise<PlaceResult[]> {
  if (!query.trim()) return [];
  try {
    const r = await getJson<{ places: PlaceResult[] }>(
      `/places?query=${encodeURIComponent(query)}&size=${size}`,
      5000
    );
    return r.places.filter((p) => p.lng != null && p.lat != null);
  } catch {
    return [];
  }
}

export interface RouteSearchReq {
  origin_lng: number;
  origin_lat: number;
  dest_lng: number;
  dest_lat: number;
  search_type?: number;
}

/** 경로 단계 (ODsay parse_path_to_steps 결과) */
export interface RouteStep {
  type: 'walk' | 'bus' | 'subway' | 'transfer' | string;
  desc?: string;
  bus_no?: string;
  bus_type?: number; // ODsay 버스 종류 코드 (3/14=마을, 4/10/11/26=광역, 그 외=일반)
  line_name?: string;
  start_name?: string;
  end_name?: string;
  station_count?: number;
  section_time?: number;
  start_x?: number;
  start_y?: number;
  end_x?: number;
  end_y?: number;
  start_id?: string;
  city_code?: string;
  pass_stops?: { name: string; lat: number; lng: number }[]; // 경유 정류장 (탑승~하차)
}

/** 대중교통 단계 색상: 지하철=파랑, 일반버스=초록, 광역버스=빨강, 마을버스=노랑 */
export const TRANSIT_COLORS = {
  subway: '#1f77b4',
  busGeneral: '#2DB400',
  busExpress: '#D32F2F',
  busVillage: '#F5B400',
  walk: '#7B1FA2',
};
const VILLAGE_TYPES = new Set([3, 14, 23]); // 마을
const EXPRESS_TYPES = new Set([4, 10, 11, 26]); // 직행좌석/광역/외곽/급행
export function transitColor(kind: 'bus' | 'subway', busType?: number): string {
  if (kind === 'subway') return TRANSIT_COLORS.subway;
  if (busType != null && VILLAGE_TYPES.has(busType)) return TRANSIT_COLORS.busVillage;
  if (busType != null && EXPRESS_TYPES.has(busType)) return TRANSIT_COLORS.busExpress;
  return TRANSIT_COLORS.busGeneral;
}

/** 경로 (parse_routes 결과) */
export interface Route {
  id: number;
  total_minutes: number;
  transfers: number;
  summary: string;
  total_walk: number;
  payment: number;
  map_obj: string;
  low_floor_bus_no: string;
  path_type: number;
  steps: RouteStep[];
}

/** 대중교통 경로 검색 (ODsay, 백엔드 /routes/search) */
export async function searchRoutes(req: RouteSearchReq) {
  return postJson<{ routes: Route[]; count: number }>('/routes/search', {
    search_type: 0,
    ...req,
  });
}

/** 저상버스 친화도 점수 (백엔드 /routes/score-low-floor) */
export interface LowFloorScore {
  id: number;
  score: number | null | 'subway_only';
  tier: number; // 0=확정/지하철, 1=부분, 2=미확인, 3=저상없음
}
export async function scoreLowFloor(routes: Route[]): Promise<LowFloorScore[]> {
  try {
    const r = await postJson<{ scores: LowFloorScore[] }>(
      '/routes/score-low-floor',
      { routes },
      30000
    );
    return r.scores;
  } catch {
    return [];
  }
}

// ─── 버스 ───
export interface BusPrediction {
  minutes?: number;
  low_floor?: boolean;
  stops_left?: string | null;
}
export interface BusArrival {
  route_name: string;
  destination?: string;
  predictions?: BusPrediction[];
}

/** 버스 도착정보 (GBIS→TAGO, 백엔드 /bus/arrivals) */
export async function busArrivals(params: {
  station_id?: string;
  lng?: number;
  lat?: number;
  station_name?: string;
}): Promise<BusArrival[]> {
  const qs = new URLSearchParams();
  if (params.station_id) qs.set('station_id', params.station_id);
  if (params.lng != null) qs.set('lng', String(params.lng));
  if (params.lat != null) qs.set('lat', String(params.lat));
  if (params.station_name) qs.set('station_name', params.station_name);
  try {
    const r = await getJson<{ arrivals: BusArrival[]; count: number }>(
      `/bus/arrivals?${qs.toString()}`
    );
    return r.arrivals;
  } catch {
    return [];
  }
}

/** 저상버스 운행/도착 여부 (백엔드 /bus/low-floor) */
export async function busLowFloor(
  busNo: string,
  stationId?: string
): Promise<boolean> {
  const qs = new URLSearchParams({ bus_no: busNo });
  if (stationId) qs.set('station_id', stationId);
  try {
    const r = await getJson<{ bus_no: string; low_floor: boolean }>(
      `/bus/low-floor?${qs.toString()}`
    );
    return r.low_floor;
  } catch {
    return false;
  }
}

// ─── 지하철 ───
export interface StationCodes {
  rail_op_cd: string;
  ln_cd: string;
  stin_cd: string;
  full_name: string;
}

/** 역명(+노선) → KRIC 역코드 (백엔드 /subway/station-codes) */
export async function stationCodes(
  stationName: string,
  lineName = ''
): Promise<StationCodes | null> {
  const qs = new URLSearchParams({ station_name: stationName, line_name: lineName });
  try {
    return await getJson<StationCodes>(`/subway/station-codes?${qs.toString()}`);
  } catch {
    return null;
  }
}

export interface NextTrain {
  minutes_until: number;
  destination: string;
  train_no: string;
  dpt_iso: string;
}
export interface NextTrainsResult {
  trains: NextTrain[];
  last_dpt: string | null;
  status: 'ok' | 'after_last' | 'no_data' | string;
}

/** 지하철 다음 열차 (백엔드 /subway/next-trains) */
export async function nextTrains(args: {
  rail_op_cd: string;
  ln_cd: string;
  stin_cd: string;
  to_stin_cd?: string;
  limit?: number;
}): Promise<NextTrainsResult> {
  const qs = new URLSearchParams({
    rail_op_cd: args.rail_op_cd,
    ln_cd: args.ln_cd,
    stin_cd: args.stin_cd,
    limit: String(args.limit ?? 3),
  });
  if (args.to_stin_cd) qs.set('to_stin_cd', args.to_stin_cd);
  try {
    return await getJson<NextTrainsResult>(`/subway/next-trains?${qs.toString()}`);
  } catch {
    return { trains: [], last_dpt: null, status: 'no_data' };
  }
}

export interface Facilities {
  movement: any[];
  elevator: any[];
  transfer: any[];
  lift: any[];
}

/** KRIC 교통약자 시설 (백엔드 /subway/facilities) */
export async function subwayFacilities(args: {
  rail_op_cd: string;
  ln_cd: string;
  stin_cd: string;
}): Promise<Facilities> {
  const qs = new URLSearchParams(args as Record<string, string>);
  try {
    // KRIC 공공 API 가 느림(배포 서버 기준 7초+) → 타임아웃 여유 있게
    return await getJson<Facilities>(`/subway/facilities?${qs.toString()}`, 30000);
  } catch {
    return { movement: [], elevator: [], transfer: [], lift: [] };
  }
}

// ─── AI 브리핑 ───
/** 지하철 방면 라벨 (백엔드 /subway/direction) — '(종점, 인접역) 방면' */
export async function subwayDirection(
  startName: string,
  endName: string,
  lineName = ''
): Promise<string> {
  const qs = new URLSearchParams({ start_name: startName, end_name: endName, line_name: lineName });
  try {
    const r = await getJson<{ label: string }>(`/subway/direction?${qs.toString()}`, 6000);
    return r.label;
  } catch {
    return endName ? `${endName} 방면` : '';
  }
}

/** 지하철 진입/하차 출구 추론 (백엔드 /subway/exits)
 *  반환: { 역명: { in?: "7번", out?: "10번" } } */
/** 역별 추천 진입/하차 출구 + 좌표 (휠체어 모드: 접근가능 출구로 제한됨) */
export interface ExitInfo {
  in?: string; // 진입 출구 라벨 (예: "7번")
  out?: string; // 하차 출구 라벨
  in_coord?: { lng: number; lat: number };
  out_coord?: { lng: number; lat: number };
}

export async function subwayExits(
  steps: RouteStep[],
  origin?: Coord,
  dest?: Coord,
  wheel = false
): Promise<Record<string, ExitInfo>> {
  try {
    const r = await postJson<{ exits: Record<string, ExitInfo> }>(
      '/subway/exits',
      { steps, origin, dest, wheel },
      15000
    );
    return r.exits || {};
  } catch {
    return {};
  }
}

/** KRIC 도면 AI 분석 (Gemini Vision, 백엔드 /subway/diagram-analysis) */
export async function diagramAnalysis(
  imgUrl: string,
  stationName = '',
  direction = ''
): Promise<string> {
  if (!imgUrl) return '';
  const qs = new URLSearchParams({ img_url: imgUrl, station_name: stationName, direction });
  try {
    const r = await getJson<{ insight: string }>(
      `/subway/diagram-analysis?${qs.toString()}`,
      20000
    );
    return r.insight || '';
  } catch {
    return '';
  }
}

/** 환승 1건의 컨텍스트 (AI 여정 내러티브 입력용) */
export interface TransferCtx {
  alight: string; // 하차 설명 (예: "망포역 정류장 (13-1번 버스 하차)")
  board: string; // 다음 승차 설명
  facility?: string; // KRIC 역내 이동경로 요약
  arrival?: string; // 다음 차량 도착/저상 정보
  walk?: string; // 환승 도보 설명
}

/** AI 여정 예행연습 내러티브 + 환승 집중 브리핑 (백엔드 /briefing/narrative, Gemini) */
export async function getNarrative(args: {
  route: Route | Record<string, unknown>;
  mode?: string;
  origin_name?: string;
  dest_name?: string;
  transfers?: TransferCtx[];
}): Promise<string> {
  try {
    const r = await postJson<{ narrative: string }>(
      '/briefing/narrative',
      { mode: 'fast', origin_name: '출발', dest_name: '도착', transfers: [], ...args },
      45000 // Gemini 생성이 느릴 수 있음
    );
    return r.narrative;
  } catch {
    return '';
  }
}

/** AI 경로 브리핑 (백엔드 /briefing) */
export async function getBriefing(args: {
  route: Route | Record<string, unknown>;
  mode?: string;
  origin_name?: string;
  dest_name?: string;
  diagram_insight?: string | null;
}): Promise<string> {
  try {
    const r = await postJson<{ briefing: string }>('/briefing', {
      mode: 'fast',
      origin_name: '출발',
      dest_name: '도착',
      ...args,
    });
    return r.briefing;
  } catch {
    return '';
  }
}
