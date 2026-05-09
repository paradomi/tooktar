"""FastAPI 백엔드 — services/ 함수를 HTTP 엔드포인트로 노출

실행: uvicorn backend.main:app --reload --port 8000
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 프로젝트 루트를 sys.path에 추가해 services 임포트 가능하게
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from services.geocode import address_to_coord
from services.odsay_api import search_pub_trans_path, parse_routes, load_lane
from services.tmap_api import pedestrian_route
from services.kakao_local import find_subway_place_id, get_subway_kakao_url


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


# ─── 엔드포인트 ───
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/geocode")
def geocode(address: str = Query(..., description="주소 또는 장소명")):
    """주소/장소명을 위경도로 변환 (카카오 REST API)"""
    coord = address_to_coord(address)
    if not coord:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다")
    return coord


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
    """Tmap 보행자 경로 — 도보 polyline 좌표"""
    coords = pedestrian_route(
        req.start_x, req.start_y, req.end_x, req.end_y,
        start_name=req.start_name, end_name=req.end_name,
        search_option=req.search_option,
    )
    if not coords:
        # 실패 시 빈 배열 반환 (프론트에서 직선 fallback 처리)
        return {"coords": [], "fallback": True}
    return {"coords": coords, "count": len(coords), "fallback": False}


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
