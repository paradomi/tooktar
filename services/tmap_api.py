"""Tmap 보행자 경로 API"""

import os
import requests


def pedestrian_route(start_x, start_y, end_x, end_y, start_name="출발", end_name="도착"):
    """Tmap 보행자 경로 API 호출.

    Returns:
        list[dict] | None: [{"lat": ..., "lng": ...}, ...] 또는 실패 시 None
    """
    api_key = os.getenv("TMAP", "")
    if not api_key:
        return None

    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
    headers = {
        "appKey": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "startX": str(start_x),
        "startY": str(start_y),
        "endX": str(end_x),
        "endY": str(end_y),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": "start",
        "endName": "end",
    }

    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        data = r.json()
        features = data.get("features", [])
        coords = []
        for feature in features:
            geometry = feature.get("geometry", {})
            if geometry.get("type") == "LineString":
                for lng, lat in geometry.get("coordinates", []):
                    coords.append({"lat": lat, "lng": lng})
        return coords if coords else None
    except Exception:
        return None
