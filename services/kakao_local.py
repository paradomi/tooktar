"""카카오 로컬 검색 — 지하철역 place_id 조회"""

import os
import requests


def find_subway_place_id(station_name: str):
    """지하철역 이름으로 카카오 place_id 검색.

    Returns:
        str | None: 카카오 place_id 또는 실패 시 None
    """
    api_key = os.getenv("KAKAO_REST_API_KEY", "")
    if not api_key or not station_name:
        return None

    # "수원시청역" → "수원시청"으로 정리하고 다시 "역" 붙여 검색
    name = station_name.rstrip()
    if name.endswith("역"):
        name = name[:-1]
    query = f"{name}역"

    url = "https://dapi.kakao.com/v2/local/search/keyword"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "category_group_code": "SW8"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
        docs = data.get("documents", [])
        if docs:
            return docs[0].get("id")
    except Exception:
        pass
    return None


def search_places(query: str, size: int = 8):
    """카카오 로컬 키워드 검색 — 자동완성용.

    Returns:
        list[dict]: 각 dict에 place_name, address_name, road_address_name, x, y 등.
                   실패/빈 결과 시 빈 리스트.
    """
    api_key = os.getenv("KAKAO_REST_API_KEY", "")
    if not api_key or not query or not query.strip():
        return []
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query.strip(), "size": size}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
        return data.get("documents", []) or []
    except Exception:
        return []


def get_subway_kakao_url(station_name: str):
    """역 이름 → 카카오맵 교통약자 페이지 URL.

    Returns:
        str | None: https://place.map.kakao.com/{id}#subwaydisad 또는 None
    """
    place_id = find_subway_place_id(station_name)
    if place_id:
        return f"https://place.map.kakao.com/{place_id}#subwaydisad"
    return None
