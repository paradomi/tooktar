"""카카오 REST API 기반 주소 → 좌표 변환"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_KEY = os.getenv("KAKAO_REST_API_KEY", "")


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
