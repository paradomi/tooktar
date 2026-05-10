"""버스 실시간 도착정보 — GBIS(경기도) + TAGO(전국) 결합."""

import os
import csv
import functools
import requests

GBIS_URL = "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"
TAGO_ARRIVAL_URL = "https://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList"
TAGO_STATION_URL = "https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getCrdntPrxmtSttnList"
TAGO_CITY_URL = "https://apis.data.go.kr/1613000/ArvlInfoInqireService/getCtyCodeList"
KAKAO_LOCAL_URL = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"


def _api_key():
    return os.getenv("GBIS_API_KEY", "")


@functools.lru_cache(maxsize=1)
def _load_city_codes():
    """data/tago_city_codes.csv → {시·도 일부 일치: citycode}"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "tago_city_codes.csv")
    mapping = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                mapping[row["cityname"]] = int(row["citycode"])
    except Exception:
        pass
    return mapping


def _is_gyeonggi_by_kakao(lng, lat):
    """카카오 reverse geocoding으로 경기도 여부 판별. 실패 시 None."""
    kakao_key = os.getenv("KAKAO_REST_API_KEY", "")
    if not kakao_key:
        return None
    try:
        r = requests.get(
            KAKAO_LOCAL_URL,
            params={"x": lng, "y": lat},
            headers={"Authorization": f"KakaoAK {kakao_key}"},
            timeout=5,
        )
        docs = r.json().get("documents", [])
        if not docs:
            return None
        region = docs[0].get("region_1depth_name", "")
        return region, "경기" in region
    except Exception:
        return None


def gbis_arrivals(station_id):
    """GBIS 도착정보 — ODsay startID 그대로 사용."""
    if not station_id:
        return []
    try:
        r = requests.get(GBIS_URL, params={
            "serviceKey": _api_key(),
            "stationId": station_id,
        }, timeout=8)
        data = r.json()
        items = data.get("response", {}).get("msgBody", {}).get("busArrivalList", [])
        if isinstance(items, dict):
            items = [items]
        out = []
        for it in items or []:
            preds = []
            for k_pred, k_low, k_loc in (
                ("predictTime1", "lowPlate1", "locationNo1"),
                ("predictTime2", "lowPlate2", "locationNo2"),
            ):
                pt = str(it.get(k_pred) or "").strip()
                if pt and pt.isdigit():
                    preds.append({
                        "minutes": int(pt),
                        "low_floor": str(it.get(k_low) or "") == "1",
                        "stops_left": str(it.get(k_loc) or "").strip() or None,
                    })
            out.append({
                "route_name": str(it.get("routeName") or ""),
                "destination": str(it.get("routeDestName") or ""),
                "flag": str(it.get("flag") or ""),
                "predictions": preds,
            })
        return out
    except Exception:
        return []


def tago_find_node_id(lng, lat):
    """좌표 → TAGO nodeId + cityCode (가장 가까운 정류장). 실패/권한 없을 시 None."""
    try:
        r = requests.get(TAGO_STATION_URL, params={
            "serviceKey": _api_key(),
            "_type": "json",
            "gpsLati": lat,
            "gpsLong": lng,
            "numOfRows": 1,
        }, timeout=6)
        if r.status_code != 200 or not r.text.strip().startswith("{"):
            return None  # 403 등 권한 미승인
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            return None
        first = items[0]
        return {"node_id": first.get("nodeid"), "city_code": first.get("citycode")}
    except Exception:
        return None


def tago_arrivals(city_code, node_id):
    """TAGO 도착정보."""
    if not city_code or not node_id:
        return []
    try:
        r = requests.get(TAGO_ARRIVAL_URL, params={
            "serviceKey": _api_key(),
            "_type": "json",
            "cityCode": city_code,
            "nodeId": node_id,
            "numOfRows": 20,
            "pageNo": 1,
        }, timeout=8)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        out = []
        for it in items or []:
            arrtime = it.get("arrtime")  # 초 단위
            preds = []
            if arrtime:
                try:
                    minutes = int(arrtime) // 60
                    preds.append({
                        "minutes": minutes,
                        "low_floor": False,  # TAGO는 저상 정보 미제공
                        "stops_left": str(it.get("arrprevstationcnt") or "").strip() or None,
                    })
                except Exception:
                    pass
            out.append({
                "route_name": str(it.get("routeno") or ""),
                "destination": "",
                "flag": "",
                "predictions": preds,
            })
        return out
    except Exception:
        return []


def get_arrivals(station_id=None, lng=None, lat=None, city_code_hint=None):
    """통합 도착정보 호출.
    1) ODsay busCityCode 또는 카카오로 경기도 판별
       - 경기도면 GBIS 우선
       - 비경기도면 TAGO 우선
    2) 우선 호출 결과 비면 다른 쪽 fallback (가능한 경우)
    """
    is_gg = None
    if city_code_hint is not None:
        # ODsay busCityCode: 1100~1199 = 경기도
        try:
            is_gg = 1100 <= int(city_code_hint) <= 1199
        except (TypeError, ValueError):
            is_gg = None
    if is_gg is None and lng is not None and lat is not None:
        result = _is_gyeonggi_by_kakao(lng, lat)
        if isinstance(result, tuple):
            is_gg = result[1]

    # 1차 시도
    if is_gg or is_gg is None:  # 경기도이거나 모를 때 GBIS 우선
        gbis = gbis_arrivals(station_id) if station_id else []
        if gbis:
            return gbis
    # TAGO fallback (정류장 검색 권한 있을 때만)
    if lng is not None and lat is not None:
        node_info = tago_find_node_id(lng, lat)
        if node_info:
            return tago_arrivals(node_info["city_code"], node_info["node_id"])
    # GBIS 마지막 시도 (비경기도였지만 station_id 있을 때)
    if station_id and not (is_gg or is_gg is None):
        return gbis_arrivals(station_id)
    return []
