"""FastAPI 백엔드 — services/ 함수를 HTTP 엔드포인트로 노출

실행: uvicorn backend.main:app --reload --port 8000
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 프로젝트 루트를 sys.path에 추가해 services 임포트 가능하게
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from services.geocode import address_to_coord, coord_to_address
from services.odsay_api import search_pub_trans_path, parse_routes, load_lane
from services.tmap_api import pedestrian_route, pedestrian_route_detail
from services.kakao_local import find_subway_place_id, get_subway_kakao_url, search_places
from services.bus_arrival import (
    get_arrivals,
    has_low_floor_arriving,
    has_low_floor_on_route,
)
from services.subway_arrival import get_next_trains
from services.rail_portal import (
    find_station_codes_on_line,
    get_station_movement,
    get_elevator_movement,
    get_transfer_movement,
    get_wheelchair_lift,
    direction_label,
)
from services.ai_briefing import (
    generate_briefing,
    analyze_subway_diagram,
    generate_journey_narrative,
)
from services.subway_exits import infer_subway_exits


app = FastAPI(title="툭타 API", version="0.1.0")

# CORS — 개발용으로 모두 허용. 운영 시 도메인 제한 권장
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic 모델 ───
class RouteSearchReq(BaseModel):
    origin_lng: float
    origin_lat: float
    dest_lng: float
    dest_lat: float
    search_type: int = 0  # 0=최단시간, 1=최소환승


class WalkReq(BaseModel):
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    start_name: str = "출발"
    end_name: str = "도착"
    search_option: int = 0  # 0=기본, 4=계단 제외


class BriefingReq(BaseModel):
    route: dict
    mode: str = "fast"
    origin_name: str = "출발"
    dest_name: str = "도착"
    diagram_insight: Optional[str] = None


class NarrativeReq(BaseModel):
    route: dict
    mode: str = "fast"
    origin_name: str = "출발"
    dest_name: str = "도착"
    # 환승 컨텍스트: [{alight, board, facility, arrival, walk}]
    transfers: list = []


class ScoreReq(BaseModel):
    routes: list


class ExitsReq(BaseModel):
    steps: list
    origin: Optional[dict] = None
    dest: Optional[dict] = None
    wheel: bool = False  # 휠체어 모드: 엘리베이터 접근가능 출구로 제한


# ─── 엔드포인트 ───
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def config():
    """클라이언트(앱)용 공개 설정 — 카카오맵 JS 키.
    JS 키는 도메인/플랫폼 등록 기반이라 노출돼도 REST 키만큼 민감하지 않음."""
    return {
        "kakao_js_key": os.getenv("KAKAO_JS_KEY") or os.getenv("KAKAO_SDK_DOMAIN", ""),
    }


@app.get("/geocode")
def geocode(address: str = Query(..., description="주소 또는 장소명")):
    """주소/장소명을 위경도로 변환 (카카오 REST API)"""
    coord = address_to_coord(address)
    if not coord:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다")
    return coord


@app.get("/reverse-geocode")
def reverse_geocode(
    lng: float = Query(..., description="경도"),
    lat: float = Query(..., description="위도"),
):
    """좌표를 주소/지명으로 변환 (카카오 REST API) — GPS 현재위치 표시용"""
    addr = coord_to_address(lng, lat)
    if not addr:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다")
    return addr


@app.get("/places")
def places(
    query: str = Query(..., description="검색어"),
    size: int = Query(8, description="결과 개수"),
):
    """카카오 키워드 검색 — 자동완성용. 좌표 포함 결과 리스트."""
    docs = search_places(query, size=size)
    results = []
    for d in docs:
        results.append({
            "place_name": d.get("place_name", ""),
            "address": d.get("road_address_name") or d.get("address_name", ""),
            "lng": float(d["x"]) if d.get("x") else None,
            "lat": float(d["y"]) if d.get("y") else None,
        })
    return {"places": results, "count": len(results)}


@app.post("/routes/search")
def search_routes(req: RouteSearchReq):
    """대중교통 경로 검색 (ODsay)"""
    result = search_pub_trans_path(
        sx=req.origin_lng, sy=req.origin_lat,
        ex=req.dest_lng, ey=req.dest_lat,
        search_type=req.search_type,
    )
    if not result:
        raise HTTPException(status_code=502, detail="ODsay 응답 없음")
    routes = parse_routes(result)
    return {"routes": routes, "count": len(routes)}


@app.get("/routes/lane")
def get_lane(map_obj: str = Query(..., description="ODsay mapObj 키")):
    """ODsay loadLane — 실제 주행 폴리라인"""
    data = load_lane(map_obj)
    if not data:
        raise HTTPException(status_code=502, detail="lane 응답 없음")
    return data


@app.post("/walk/pedestrian")
def walk_pedestrian(req: WalkReq):
    """Tmap 보행자 경로 — 도보 polyline 좌표 + 턴바이턴 안내(guides)"""
    coords, guides = pedestrian_route_detail(
        req.start_x, req.start_y, req.end_x, req.end_y,
        start_name=req.start_name, end_name=req.end_name,
        search_option=req.search_option,
    )
    if not coords:
        # 실패 시 빈 배열 반환 (프론트에서 직선 fallback 처리)
        return {"coords": [], "guides": [], "fallback": True}
    return {"coords": coords, "guides": guides, "count": len(coords), "fallback": False}


@app.get("/subway/place-id")
def subway_place_id(name: str = Query(..., description="지하철역 이름")):
    """역 이름 → 카카오 place_id"""
    place_id = find_subway_place_id(name)
    if not place_id:
        raise HTTPException(status_code=404, detail="역을 찾을 수 없습니다")
    return {"name": name, "place_id": place_id}


@app.get("/subway/url")
def subway_url(name: str = Query(..., description="지하철역 이름")):
    """역 이름 → 카카오맵 교통약자 페이지 URL"""
    url = get_subway_kakao_url(name)
    if not url:
        raise HTTPException(status_code=404, detail="역을 찾을 수 없습니다")
    return {"name": name, "url": url}


@app.get("/bus/arrivals")
def bus_arrivals(
    station_id: Optional[str] = Query(None, description="GBIS stationId (있으면 우선)"),
    lng: Optional[float] = Query(None, description="정류장 경도"),
    lat: Optional[float] = Query(None, description="정류장 위도"),
    station_name: Optional[str] = Query(None, description="정류장 이름"),
):
    """버스 도착정보 (GBIS 우선 → TAGO fallback)"""
    arrivals = get_arrivals(
        station_id=station_id, lng=lng, lat=lat, station_name=station_name
    )
    return {"arrivals": arrivals, "count": len(arrivals)}


@app.get("/bus/low-floor")
def bus_low_floor(
    bus_no: str = Query(..., description="노선번호"),
    station_id: Optional[str] = Query(None, description="GBIS stationId"),
    max_stops_ahead: int = Query(30, description="정류장 이내 저상 차량 검색 범위"),
):
    """저상버스 운행/도착 여부 판별"""
    if station_id:
        is_low = has_low_floor_arriving(station_id, bus_no, max_stops_ahead=max_stops_ahead)
    else:
        is_low = has_low_floor_on_route(bus_no)
    return {"bus_no": bus_no, "low_floor": bool(is_low)}


@app.get("/subway/station-codes")
def subway_station_codes(
    station_name: str = Query(..., description="역명"),
    line_name: str = Query("", description="노선명 (환승역 구분용)"),
):
    """역명(+노선) → KRIC 역코드"""
    codes = find_station_codes_on_line(station_name, line_name)
    if not codes:
        raise HTTPException(status_code=404, detail="역코드를 찾을 수 없습니다")
    rail_op, ln_cd, stin_cd, full_name = codes
    return {
        "rail_op_cd": rail_op,
        "ln_cd": ln_cd,
        "stin_cd": stin_cd,
        "full_name": full_name,
    }


@app.get("/subway/next-trains")
def subway_next_trains(
    rail_op_cd: str = Query(..., description="운영기관코드"),
    ln_cd: str = Query(..., description="노선코드"),
    stin_cd: str = Query(..., description="역코드"),
    limit: int = Query(3, description="최대 열차 수"),
    to_stin_cd: Optional[str] = Query(None, description="하차역 코드 (방향 필터)"),
):
    """지하철 다음 열차 (KRIC 시각표, KST 기준)"""
    return get_next_trains(
        rail_op_cd, ln_cd, stin_cd, limit=limit, to_stin_cd=to_stin_cd
    )


@app.get("/subway/facilities")
def subway_facilities(
    rail_op_cd: str = Query(..., description="운영기관코드"),
    ln_cd: str = Query(..., description="노선코드"),
    stin_cd: str = Query(..., description="역코드"),
):
    """KRIC 교통약자 시설 (이동경로/엘리베이터/환승/휠체어리프트)"""
    return {
        "movement": get_station_movement(rail_op_cd, ln_cd, stin_cd),
        "elevator": get_elevator_movement(rail_op_cd, ln_cd, stin_cd),
        "transfer": get_transfer_movement(rail_op_cd, ln_cd, stin_cd),
        "lift": get_wheelchair_lift(rail_op_cd, ln_cd, stin_cd),
    }


@app.get("/subway/direction")
def subway_direction(
    start_name: str = Query(..., description="승차역명"),
    end_name: str = Query(..., description="하차역명"),
    line_name: str = Query("", description="노선명"),
):
    """지하철 방면 라벨 — '(종점, 인접역) 방면'"""
    label = direction_label(start_name, end_name, line_name or None)
    return {"label": label}


@app.post("/subway/exits")
def subway_exits(req: ExitsReq):
    """지하철 진입/하차 출구 추론. 반환: {역명: {"in": "7번", "out": "10번"}}
    wheel=True면 각 역의 엘리베이터 접근가능 출구로 추천을 제한한다."""
    import re as _re
    accessible = None
    if req.wheel:
        # 경로의 지하철 역마다 KRIC 이동경로에서 엘리베이터 접근가능 출구 번호 집합 추출
        accessible = {}
        seen = set()
        for s in req.steps:
            if s.get("type") != "subway":
                continue
            for nm in (s.get("start_name"), s.get("end_name")):
                if not nm or nm in seen:
                    continue
                seen.add(nm)
                codes = find_station_codes_on_line(nm, s.get("line_name", "") or "")
                if not codes:
                    continue
                rail_op, ln_cd, stin_cd, _full = codes
                mv = get_station_movement(rail_op, ln_cd, stin_cd)
                nums = set()
                for it in mv or []:
                    for n in _re.findall(r"(\d+)번", it.get("stMovePath", "") or ""):
                        nums.add(n)
                if nums:
                    accessible[nm] = nums
        accessible = accessible or None
    exits = infer_subway_exits(req.steps, req.origin, req.dest, accessible_map=accessible)
    return {"exits": exits}


@app.post("/briefing")
def briefing(req: BriefingReq):
    """AI 경로 브리핑 (템플릿 + 선택적 도면 인사이트)"""
    text = generate_briefing(
        req.route,
        req.mode,
        req.origin_name,
        req.dest_name,
        diagram_insight=req.diagram_insight,
    )
    return {"briefing": text}


@app.post("/briefing/narrative")
def briefing_narrative(req: NarrativeReq):
    """AI 여정 예행연습 내러티브 + 환승 집중 브리핑 (Gemini 텍스트 생성).
    Gemini 실패 시 빈 문자열 → 클라이언트는 템플릿 브리핑만 표시."""
    text = generate_journey_narrative(
        req.route, req.mode, req.origin_name, req.dest_name, transfers=req.transfers
    )
    return {"narrative": text or ""}


@app.get("/subway/diagram-analysis")
def diagram_analysis(
    img_url: str = Query(..., description="KRIC 역내 도면 imgPath"),
    station_name: str = Query("", description="역명"),
    direction: str = Query("", description="가야 할 방면"),
):
    """KRIC 도면 이미지를 Gemini Vision으로 분석해 휠체어 이용자용 안내 생성."""
    insight = analyze_subway_diagram(img_url, station_name, direction)
    return {"insight": insight or ""}


def _bus_check_jobs(route):
    """경로의 버스 step별 (station_id, bus_no, timed) 생성.
    timed=True는 경로의 첫 대중교통이 이 버스인 경우 — 그때만 '지금부터 25분 이내' 기준이 유효.
    환승 버스는 도착 시점을 알 수 없으므로 노선 저상 운행 여부로만 판정."""
    steps = route.get("steps", []) or []
    first_transit_idx = next(
        (i for i, s in enumerate(steps) if s.get("type") in ("bus", "subway")), -1
    )
    out = []
    for i, s in enumerate(steps):
        if s.get("type") != "bus":
            continue
        bus_no = s.get("bus_no", "")
        if not bus_no:
            continue
        timed = i == first_transit_idx
        station_id = s.get("start_id") if timed else None
        out.append((station_id, bus_no, timed))
    return out


@app.post("/routes/score-low-floor")
def score_low_floor(req: ScoreReq):
    """경로별 저상버스 친화도 점수 (저상 조회를 중복 제거 + 병렬 처리).
    반환: [{"id", "score", "tier"}]
      score: 1.0=전 구간 저상확보, 0~1=부분, 0=저상없음, null=미확인, "subway_only"=버스없음
      tier:  0=확정/지하철, 1=부분, 2=미확인, 3=저상없음 (작을수록 우선)
    저상 확보 판정: 첫 대중교통이 버스인 step만 25분 이내 도착 기준, 환승 버스는 노선 저상 운행 여부 기준.
    """
    # 1) 모든 경로의 버스 step에서 필요한 검사를 중복 제거 (timed 여부 포함)
    jobs = {}  # (station_id_or_empty, bus_no, timed) -> (station_id, bus_no, timed)
    for route in req.routes:
        for station_id, bus_no, timed in _bus_check_jobs(route):
            key = (station_id or "", bus_no, timed)
            if key not in jobs:
                jobs[key] = (station_id, bus_no, timed)

    # 2) 병렬로 저상 운행 여부 조회
    def _check(item):
        station_id, bus_no, timed = item
        try:
            if timed and station_id:
                return has_low_floor_arriving(station_id, bus_no, max_stops_ahead=15, fast=True, max_wait_min=25)
            # 환승 버스(또는 정류장 매칭 불가): 노선에 저상 차량 운행 중인지로 판정
            return has_low_floor_on_route(bus_no)
        except Exception:
            return False

    cache = {}  # key -> bool
    if jobs:
        keys = list(jobs.keys())
        workers = min(len(keys), 16) or 1
        with ThreadPoolExecutor(max_workers=workers) as ex:
            vals = list(ex.map(lambda k: _check(jobs[k]), keys))
        cache = dict(zip(keys, vals))

    # 3) 캐시를 읽어 경로별 점수 계산 (네트워크 호출 없음)
    results = []
    for route in req.routes:
        rid = route.get("id")
        bus_steps = [s for s in (route.get("steps", []) or []) if s.get("type") == "bus"]
        if not bus_steps:
            results.append({"id": rid, "score": "subway_only", "tier": 0})
            continue

        ok = 0
        data_steps = 0
        for station_id, bus_no, timed in _bus_check_jobs(route):
            key = (station_id or "", bus_no, timed)
            data_steps += 1
            if bool(cache.get(key, False)):
                ok += 1

        if data_steps == 0:
            score = None
        else:
            score = ok / data_steps

        if score == 1.0:
            tier = 0
        elif isinstance(score, (int, float)) and score > 0:
            tier = 1
        elif score is None:
            tier = 2
        else:
            tier = 3
        results.append({"id": rid, "score": score, "tier": tier})

    return {"scores": results}
