"""ODsay 대중교통 길찾기 API - searchPubTransPathT + loadLane"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ODSAY_KEY = os.getenv("ODSAY_API_KEY", "")
BASE = "https://api.odsay.com/v1/api"
HEADERS = {"Referer": "http://localhost:8501"}


def search_pub_trans_path(sx, sy, ex, ey, search_type=0):
    """대중교통 경로 검색. search_type: 0=최단시간, 1=최소환승"""
    url = f"{BASE}/searchPubTransPathT"
    params = {
        "SX": sx, "SY": sy,
        "EX": ex, "EY": ey,
        "OPT": search_type,
        "SearchType": 0,
        "SearchPathType": 0,
        "apiKey": ODSAY_KEY,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = r.json()
        if "result" in data:
            return data["result"]
    except Exception:
        pass
    return None


def load_lane(map_obj: str):
    """mapObj 값으로 실제 주행 경로(폴리라인 좌표) 조회. 0:0@ 접두사 필요."""
    formatted = f"0:0@{map_obj}" if not map_obj.startswith("0:0@") else map_obj
    url = f"{BASE}/loadLane?mapObject={formatted}&apiKey={ODSAY_KEY}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        if "result" in data:
            return data["result"]
    except Exception:
        pass
    return None


def parse_path_to_steps(path_info: dict) -> list[dict]:
    """ODsay 경로 응답의 subPath를 UI용 step 리스트로 변환"""
    steps = []
    sub_paths = path_info.get("subPath", [])
    for i, sp in enumerate(sub_paths):
        traffic_type = sp.get("trafficType")  # 1=지하철, 2=버스, 3=도보
        distance = sp.get("distance", 0)
        section_time = sp.get("sectionTime", 0)

        if traffic_type == 3:
            start_name = sp.get("startName", "")
            end_name = sp.get("endName", "")
            steps.append({
                "step": len(steps) + 1,
                "type": "walk",
                "desc": f"도보 {section_time}분 ({distance}m)",
                "barrier_free": True,
                "section_time": section_time,
                "start_name": start_name,
                "end_name": end_name,
                "start_x": sp.get("startX"),
                "start_y": sp.get("startY"),
                "end_x": sp.get("endX"),
                "end_y": sp.get("endY"),
            })
        elif traffic_type == 2:
            lane = sp.get("lane", [{}])
            bus_no = lane[0].get("busNo", "") if lane else ""
            bus_type = lane[0].get("type", 0) if lane else 0
            start_name = sp.get("startName", "")
            end_name = sp.get("endName", "")
            station_count = sp.get("stationCount", 0)
            is_low_floor = bus_type in [1, 4]
            steps.append({
                "step": len(steps) + 1,
                "type": "bus",
                "desc": f"{bus_no}번 버스 ({start_name} → {end_name}, {station_count}정거장, {section_time}분)",
                "barrier_free": is_low_floor,
                "bus_no": bus_no,
                "bus_type": bus_type,
                "start_name": start_name,
                "end_name": end_name,
                "station_count": station_count,
                "section_time": section_time,
                "start_x": sp.get("startX"),
                "start_y": sp.get("startY"),
                "end_x": sp.get("endX"),
                "end_y": sp.get("endY"),
            })
        elif traffic_type == 1:
            lane = sp.get("lane", [{}])
            line_name = lane[0].get("name", "") if lane else ""
            start_name = sp.get("startName", "")
            end_name = sp.get("endName", "")
            station_count = sp.get("stationCount", 0)
            steps.append({
                "step": len(steps) + 1,
                "type": "subway",
                "desc": f"{line_name} ({start_name} → {end_name}, {station_count}역, {section_time}분)",
                "barrier_free": True,
                "line_name": line_name,
                "start_name": start_name,
                "end_name": end_name,
                "station_count": station_count,
                "section_time": section_time,
            })
    return steps


def parse_routes(result: dict) -> list[dict]:
    """ODsay 전체 응답을 UI용 경로 리스트로 변환"""
    routes = []
    paths = result.get("path", [])
    for idx, path in enumerate(paths):
        info = path.get("info", {})
        path_type = path.get("pathType")  # 1=지하철, 2=버스, 3=버스+지하철
        type_label = {1: "지하철", 2: "버스", 3: "버스+지하철"}.get(path_type, "대중교통")

        steps = parse_path_to_steps(path)
        bus_steps = [s for s in steps if s["type"] == "bus"]
        bus_nos = [s.get("bus_no", "") for s in bus_steps]

        routes.append({
            "id": idx + 1,
            "total_minutes": info.get("totalTime", 0),
            "transfers": info.get("busTransitCount", 0) + info.get("subwayTransitCount", 0),
            "barrier_free_score": 80,
            "is_step_free": False,
            "low_floor_arrival": "",
            "low_floor_bus_no": ", ".join(bus_nos) if bus_nos else "-",
            "summary": f"{type_label} · 총 {info.get('totalDistance', 0)//1000}km",
            "total_walk": info.get("totalWalk", 0),
            "payment": info.get("payment", 0),
            "map_obj": info.get("mapObj", ""),
            "steps": steps,
            "path_type": path_type,
        })
    return routes
