"""카카오 REST API 기반 주소 → 좌표 변환"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_KEY = os.getenv("KAKAO_REST_API_KEY", "")


def coord_to_address(lng: float, lat: float) -> dict | None:
    """카카오 좌표→주소 변환.
    Returns: {"name": "...", "address": "...", "lng": lng, "lat": lat} or None
    name은 행정동(법정동 우선), address는 전체 주소.
    """
    if lng is None or lat is None:
        return None
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params = {"x": lng, "y": lat, "input_coord": "WGS84"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
        docs = data.get("documents", [])
        if not docs:
            return None
        doc = docs[0]
        road = doc.get("road_address") or {}
        addr_dict = doc.get("address") or {}
        full_address = (
            road.get("address_name")
            or addr_dict.get("address_name", "")
        )
        short_name = ""
        if addr_dict.get("region_2depth_name") and addr_dict.get("region_3depth_name"):
            short_name = f"{addr_dict['region_2depth_name']} {addr_dict['region_3depth_name']}"
        elif road.get("region_2depth_name"):
            short_name = road["region_2depth_name"]
        return {
            "name": short_name or full_address or "현재 위치",
            "address": full_address,
            "lng": float(lng),
            "lat": float(lat),
        }
    except Exception:
        return None


def address_to_coord(query: str) -> dict | None:
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params = {"query": query, "size": 1}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
        if data.get("documents"):
            doc = data["documents"][0]
            return {
                "name": doc.get("place_name", query),
                "address": doc.get("address_name", ""),
                "lng": float(doc["x"]),
                "lat": float(doc["y"]),
            }
    except Exception:
        pass
    return None
