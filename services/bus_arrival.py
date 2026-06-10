"""버스 실시간 도착정보 — GBIS(경기도) + TAGO(전국) 결합."""

import os
import csv
import functools
import requests

GBIS_URL = "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"
GBIS_LOCATION_URL = "https://apis.data.go.kr/6410000/buslocationservice/v2/getBusLocationListv2"
GBIS_ROUTE_URL = "https://apis.data.go.kr/6410000/busrouteservice/v2/getBusRouteListv2"
GBIS_STATION_URL = "https://apis.data.go.kr/6410000/busstationservice/v2/getBusStationListv2"
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


def _gbis_arrivals_raw(station_id):
    """GBIS 도착정보 — stationId 직접 호출."""
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


@functools.lru_cache(maxsize=512)
def gbis_find_station_id(station_name, lng_int, lat_int):
    """ODsay 정류장명 + 좌표로 GBIS stationId 검색. lru 캐시.
    lng_int/lat_int: 좌표 * 100000 정수 (캐시 키 안정성)."""
    if not station_name:
        return None
    lng, lat = lng_int / 100000.0, lat_int / 100000.0
    try:
        kw = station_name.split(".")[0].split(",")[0].split("(")[0].strip()
        if len(kw) < 2:
            return None
        r = requests.get(GBIS_STATION_URL, params={
            "serviceKey": _api_key(),
            "keyword": kw,
        }, timeout=6)
        items = r.json().get("response", {}).get("msgBody", {}).get("busStationList", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            return None
        items.sort(key=lambda it: ((float(it.get("x", 0)) - lng) ** 2 +
                                    (float(it.get("y", 0)) - lat) ** 2))
        first = items[0]
        # 좌표 거리 너무 크면 매칭 거부 (약 1km 이상)
        dx = float(first.get("x", 0)) - lng
        dy = float(first.get("y", 0)) - lat
        if dx * dx + dy * dy > 0.0001:
            return None
        return first.get("stationId")
    except Exception:
        return None


def gbis_arrivals(station_id, station_name=None, lng=None, lat=None):
    """GBIS 도착정보. station_id로 우선 시도, 실패 시 좌표+이름으로 GBIS stationId 재매핑."""
    out = _gbis_arrivals_raw(station_id) if station_id else []
    if out:
        return out
    # Fallback: ODsay startName + 좌표로 GBIS stationId 검색
    if station_name and lng is not None and lat is not None:
        try:
            new_sid = gbis_find_station_id(
                station_name, int(round(lng * 100000)), int(round(lat * 100000))
            )
        except Exception:
            new_sid = None
        if new_sid and new_sid != station_id:
            return _gbis_arrivals_raw(new_sid)
    return []


def gbis_bus_locations(route_id):
    """GBIS BusLocationService — 노선 운행 중 모든 차량 위치 + 저상 여부.
    Returns: [{vehicle, station_seq, low_plate, plate_no, station_id}, ...]
    권한/응답 실패 시 빈 리스트.
    """
    if not route_id:
        return []
    try:
        r = requests.get(GBIS_LOCATION_URL, params={
            "serviceKey": _api_key(),
            "routeId": route_id,
            "format": "json",
        }, timeout=8)
        if r.status_code != 200 or not r.text.strip().startswith("{"):
            return []
        items = r.json().get("response", {}).get("msgBody", {}).get("busLocationList", [])
        if isinstance(items, dict):
            items = [items]
        out = []
        for v in items or []:
            # GBIS는 필드명이 케이스마다 다양 — stationSeq, staOrder 등 모두 시도
            seq = (
                v.get("stationSeq") or v.get("staOrder")
                or v.get("nodeSeq") or v.get("stationNo")
            )
            try:
                seq = int(seq) if seq is not None else None
            except (ValueError, TypeError):
                seq = None
            out.append({
                "vehicle_id": v.get("vehId") or v.get("vehicleId"),
                "plate_no": str(v.get("plateNo") or ""),
                "station_seq": seq,
                "station_id": v.get("stationId"),
                "low_plate": str(v.get("lowPlate") or "") == "1",
                "end_bus": str(v.get("endBus") or "") == "1",
            })
        return out
    except Exception:
        return []


def gbis_find_route_ids(bus_no):
    """노선번호 정확 매칭으로 routeId 목록 반환 (지역 다양 가능).
    keyword 검색은 부분매칭이라 routeName==bus_no인 것만 필터.
    """
    if not bus_no:
        return []
    try:
        r = requests.get(GBIS_ROUTE_URL, params={
            "serviceKey": _api_key(),
            "keyword": bus_no,
        }, timeout=8)
        items = r.json().get("response", {}).get("msgBody", {}).get("busRouteList", [])
        if isinstance(items, dict):
            items = [items]
        return [
            it for it in (items or [])
            if str(it.get("routeName")) == str(bus_no)
        ]
    except Exception:
        return []


def has_low_floor_on_route(bus_no, region_hint=None):
    """노선번호로 같은 routeName 모든 노선의 BusLocation을 확인,
    저상 차량이 운행 중인지 검증.

    Args:
        bus_no: 노선번호 (예: "80")
        region_hint: 지역 키워드 (예: "수원") — 같은 번호 여러 노선 중 매칭에 우선

    Returns:
        bool: 저상 차량 운행 중이면 True
    """
    routes = gbis_find_route_ids(bus_no)
    if not routes:
        return False
    # 지역 힌트로 우선 정렬 (수원 매칭이 앞에 오도록)
    if region_hint:
        routes.sort(key=lambda r: 0 if region_hint in (r.get("regionName", "") + r.get("adminName", "")) else 1)
    # 최대 3개까지만 시도 (응답 시간 보호)
    for r in routes[:3]:
        rid = r.get("routeId")
        if not rid:
            continue
        vehicles = gbis_bus_locations(rid)
        for v in vehicles or []:
            if v.get("low_plate") and not v.get("end_bus"):
                return True
    return False


def has_low_floor_arriving(station_id, route_name, max_stops_ahead=30, fast=False):
    """특정 정류장에 곧 도착하는 저상버스가 노선에 있는지.

    1) GBIS 도착정보로 routeId + 우리 정류장 staOrder 알아냄
    2) 도착예정 첫 두 대(lowPlate1/2) 중 저상이면 즉시 True
    3) 아니면 노선 차량 위치(BusLocation) 조회 → 저상 차량 중 우리 정류장
       이전(staOrder 차이 1~max_stops_ahead) 차량 있으면 True
    """
    if not station_id or not route_name:
        return False
    try:
        r = requests.get(GBIS_URL, params={
            "serviceKey": _api_key(),
            "stationId": station_id,
        }, timeout=(4 if fast else 6))
        items = r.json().get("response", {}).get("msgBody", {}).get("busArrivalList", [])
        if isinstance(items, dict):
            items = [items]
    except Exception:
        return False

    matched = next((it for it in (items or []) if str(it.get("routeName")) == route_name), None)
    if not matched:
        # 정류장 매칭 실패 (ODsay startID ≠ GBIS stationId인 경우)
        if fast:
            # 빠른 모드: 무거운 노선검색 폴백 생략
            return False
        # → 노선번호로 직접 routeId 찾아 BusLocation에서 저상 운행 검증
        return has_low_floor_on_route(route_name)

    # 도착예정 첫 두 대 중 저상 있으면 즉시 True
    for k in ("lowPlate1", "lowPlate2"):
        if str(matched.get(k) or "") == "1":
            return True

    # 빠른 모드: 다음 버스가 40분 넘게 남았으면 무거운 위치조회 생략
    if fast:
        try:
            _pt = int(matched.get("predictTime1"))
            if _pt > 40:
                return False
        except (ValueError, TypeError):
            pass  # 도착시간 모르면 그대로 검증 진행

    route_id = matched.get("routeId")
    try:
        sta_order = int(matched.get("staOrder"))
    except (ValueError, TypeError):
        sta_order = None

    if not route_id:
        if fast:
            return False
        return has_low_floor_on_route(route_name)

    # 노선 전체 차량 위치
    vehicles = gbis_bus_locations(route_id)
    if not vehicles:
        return False

    # staOrder 측정 가능하면 거리 제한 적용
    if sta_order is not None:
        for v in vehicles:
            if not v.get("low_plate") or v.get("end_bus"):
                continue
            v_seq = v.get("station_seq")
            if v_seq is None:
                continue
            diff = sta_order - v_seq
            if 0 < diff <= max_stops_ahead:
                return True
        return False

    # staOrder 알 수 없으면 노선에 저상 차량 운행 중인지만 검사
    for v in vehicles:
        if v.get("low_plate") and not v.get("end_bus"):
            return True
    return False


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


def get_arrivals(station_id=None, lng=None, lat=None, city_code_hint=None, station_name=None):
    """통합 도착정보 호출 (속도 최적화).
    GBIS(경기도) 먼저 시도 → 빈 결과면 TAGO(전국) fallback.
    카카오 지역 판별 호출은 제거 — GBIS가 빈 결과면 자연히 TAGO로 넘어가므로
    별도 reverse geocoding 불필요(정류장당 1회 호출·최대 5초 절감).
    """
    gbis = gbis_arrivals(station_id, station_name=station_name, lng=lng, lat=lat)
    if gbis:
        return gbis
    if lng is not None and lat is not None:
        node_info = tago_find_node_id(lng, lat)
        if node_info:
            return tago_arrivals(node_info["city_code"], node_info["node_id"])
    return []
