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


def find_station_exits(station_name: str, max_exits: int = 12):
    """역의 출구 좌표 검색 → {출구번호(int): (lng, lat)}.

    카카오에 '{역명}역 N번 출구'로 N=1..max_exits 각각 검색.
    - 카카오는 broad 쿼리(`{역명}역 출구`)에 출구 POI를 안 돌려주므로 per-N 호출이 필요
    - 카카오는 존재하지 않는 번호 검색 시 다른 역의 같은 번호를 돌려주는 버그가 있어
      반드시 result place_name에 `{역명}역` 이 그대로 포함돼야 통과
    - 출구/출입구, 공백 변형 모두 허용
    """
    import re
    from concurrent.futures import ThreadPoolExecutor
    if not station_name:
        return {}
    nm = station_name.rstrip("역").strip()
    if not nm:
        return {}
    nm_clean = nm.replace(" ", "")
    target_token = f"{nm_clean}역"  # 예: "야탑역", "수원시청역"

    def _probe(n):
        """N번 출구 1개 조회 → (n, (lng, lat)) 또는 None."""
        docs = search_places(f"{nm}역 {n}번 출구", size=1)
        if not docs:
            return None
        d = docs[0]
        place_raw = d.get("place_name") or ""
        place = place_raw.replace(" ", "")
        if target_token not in place:  # 다른 역 동일 번호 차단
            return None
        if not re.search(rf"\b{n}번\s*출[구입]구?", place_raw) and not re.search(rf"{n}번출[구입]구?", place):
            return None
        try:
            return (n, (float(d["x"]), float(d["y"])))
        except (KeyError, TypeError, ValueError):
            return None

    # N=1..max_exits 동시 조회 (순차 12회 → 병렬)
    exits = {}
    with ThreadPoolExecutor(max_workers=max_exits) as ex:
        for res in ex.map(_probe, range(1, max_exits + 1)):
            if res:
                exits[res[0]] = res[1]
    return exits


def find_nearest_exit(station_name: str, lng: float, lat: float):
    """주어진 좌표에 가장 가까운 출구 번호 반환. 못 찾으면 None."""
    if lng is None or lat is None:
        return None
    exits = find_station_exits(station_name)
    if not exits:
        return None
    best_no = None
    best_dist = float("inf")
    for no, (ex_lng, ex_lat) in exits.items():
        d = (ex_lng - lng) ** 2 + (ex_lat - lat) ** 2
        if d < best_dist:
            best_dist = d
            best_no = no
    return best_no


def get_subway_kakao_url(station_name: str):
    """역 이름 → 카카오맵 교통약자 페이지 URL.

    Returns:
        str | None: https://place.map.kakao.com/{id}#subwaydisad 또는 None
    """
    place_id = find_subway_place_id(station_name)
    if place_id:
        return f"https://place.map.kakao.com/{place_id}#subwaydisad"
    return None
