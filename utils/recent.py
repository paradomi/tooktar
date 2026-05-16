"""최근 검색 경로 저장/조회 — data/recent.json 영속화."""

import os
import json

MAX_RECENT = 5

def _path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "recent.json",
    )

def load_recent():
    """최근 검색 리스트 반환. 파일 없으면 빈 리스트."""
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def save_recent(items):
    """최근 검색 리스트 저장."""
    try:
        os.makedirs(os.path.dirname(_path()), exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_recent(origin_coord, dest_coord, origin_name, dest_name):
    """새 검색을 최근 목록 맨 앞에 추가. 중복(같은 origin+dest 좌표)은 합쳐서 위로.
    좌표는 dict({name, address, lng, lat}).
    """
    if not origin_coord or not dest_coord:
        return
    items = load_recent()
    o_lng = origin_coord.get("lng")
    o_lat = origin_coord.get("lat")
    d_lng = dest_coord.get("lng")
    d_lat = dest_coord.get("lat")
    # 중복 제거 (좌표 0.0001 이내면 동일 취급)
    def _eq(a, b):
        try:
            return abs(float(a) - float(b)) < 0.0001
        except (TypeError, ValueError):
            return False
    items = [
        it for it in items
        if not (
            _eq(it.get("origin", {}).get("lng"), o_lng)
            and _eq(it.get("origin", {}).get("lat"), o_lat)
            and _eq(it.get("dest", {}).get("lng"), d_lng)
            and _eq(it.get("dest", {}).get("lat"), d_lat)
        )
    ]
    items.insert(0, {
        "origin": {
            "name": origin_name or origin_coord.get("name", ""),
            "address": origin_coord.get("address", ""),
            "lng": o_lng, "lat": o_lat,
        },
        "dest": {
            "name": dest_name or dest_coord.get("name", ""),
            "address": dest_coord.get("address", ""),
            "lng": d_lng, "lat": d_lat,
        },
    })
    save_recent(items[:MAX_RECENT])

def remove_recent(index):
    """인덱스 위치의 최근 검색 항목 삭제."""
    items = load_recent()
    if 0 <= index < len(items):
        del items[index]
        save_recent(items)
