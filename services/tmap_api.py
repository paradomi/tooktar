"""Tmap 보행자 경로 API"""

import os
import requests


def pedestrian_route(start_x, start_y, end_x, end_y, start_name="출발", end_name="도착", search_option=0):
    """Tmap 보행자 경로 API 호출.

    Returns:
        list[dict] | None: [{"lat": ..., "lng": ...}, ...] 또는 실패 시 None
    """
    coords, _ = pedestrian_route_detail(
        start_x, start_y, end_x, end_y, start_name, end_name, search_option
    )
    return coords


def pedestrian_route_detail(start_x, start_y, end_x, end_y, start_name="출발", end_name="도착", search_option=0):
    """Tmap 보행자 경로 — 폴리라인 좌표 + 턴바이턴 안내.

    Returns:
        (coords, guides):
          coords: [{"lat","lng"}, ...]  (실패 시 None)
          guides: [{"turn_type","description","distance","lat","lng"}, ...]
                  Point feature(꺾이는 지점)별 안내. 거리는 그 지점 이후 구간 길이(m).
    """
    api_key = os.getenv("TMAP", "")
    if not api_key:
        return None, []

    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
    headers = {"appKey": api_key, "Content-Type": "application/json"}
    body = {
        "startX": str(start_x),
        "startY": str(start_y),
        "endX": str(end_x),
        "endY": str(end_y),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": "start",
        "endName": "end",
        "searchOption": str(search_option),
    }

    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        data = r.json()
        features = data.get("features", [])
        coords = []
        guides = []
        # Tmap features: Point(꺾이는 지점, turnType/description) + LineString(구간, distance) 교대
        # 각 Point 안내에 "그 다음 LineString 구간 거리"를 붙여 "직진 261m" 형태로 구성
        for i, feature in enumerate(features):
            geometry = feature.get("geometry", {})
            props = feature.get("properties", {})
            gtype = geometry.get("type")
            if gtype == "LineString":
                for lng, lat in geometry.get("coordinates", []):
                    coords.append({"lat": lat, "lng": lng})
            elif gtype == "Point":
                lng, lat = geometry.get("coordinates", [None, None])
                if lng is None or lat is None:
                    continue
                # 다음 LineString feature의 distance(이 지점 이후 이동 거리)
                next_dist = 0
                for j in range(i + 1, len(features)):
                    if features[j].get("geometry", {}).get("type") == "LineString":
                        next_dist = features[j].get("properties", {}).get("distance", 0) or 0
                        break
                guides.append({
                    "turn_type": props.get("turnType", 0),
                    "description": props.get("description", ""),
                    "distance": int(next_dist),
                    "lat": lat,
                    "lng": lng,
                })
        return (coords if coords else None), guides
    except Exception:
        return None, []
