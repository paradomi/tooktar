"""철도산업정보센터(KRIC) 레일포털 API — 역내 교통약자 이동 경로/엘리베이터/리프트 정보"""

import os
import functools
import requests
import pandas as pd

KRIC_BASE = "https://openapi.kric.go.kr/openapi"


@functools.lru_cache(maxsize=1)
def _load_station_codes():
    """프로젝트 data/station_codes.csv 로드 → 역명 검색용"""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "station_codes.csv",
    )
    try:
        return pd.read_csv(csv_path)
    except Exception:
        return None


def find_station_codes(station_name: str):
    """역명으로 (railOprIsttCd, lnCd, stinCd, 매칭된역명) 반환. 못 찾으면 None.

    예: '수원시청' → ('KR', 'K1', 'K243', '수원시청(경기도청화성청)')
        '수원시청역' → 동일 ('역' 접미사 자동 제거)
    """
    if not station_name:
        return None
    df = _load_station_codes()
    if df is None or df.empty:
        return None

    name = station_name.strip()
    if name.endswith("역"):
        name = name[:-1]

    # 정확 매칭 우선
    exact = df[df["STIN_NM"] == name]
    if not exact.empty:
        row = exact.iloc[0]
    else:
        # 부분 매칭 (예: "수원시청" → "수원시청(...)")
        partial = df[df["STIN_NM"].str.startswith(name, na=False)]
        if partial.empty:
            return None
        row = partial.iloc[0]
    return (
        str(row["RAIL_OPR_ISTT_CD"]),
        str(row["LN_CD"]),
        str(row["STIN_CD"]),
        str(row["STIN_NM"]),
    )


def _call_kric(service_id: str, op_id: str, **params):
    """KRIC API 공통 호출 헬퍼. 실패 시 빈 리스트."""
    api_key = os.getenv("KRIC", "")
    if not api_key:
        return []
    url = f"{KRIC_BASE}/{service_id}/{op_id}"
    qs = {"serviceKey": api_key, "format": "json", **params}
    try:
        r = requests.get(url, params=qs, timeout=8)
        data = r.json()
        if data.get("header", {}).get("resultCode") == "00":
            return data.get("body", []) or []
    except Exception:
        pass
    return []


def get_station_movement(rail_op_cd, ln_cd, stin_cd):
    """장애인 역내 이동 경로 (도면+단계)"""
    return _call_kric(
        "handicapped", "stationMovement",
        railOprIsttCd=rail_op_cd, lnCd=ln_cd, stinCd=stin_cd,
    )


def get_elevator_movement(rail_op_cd, ln_cd, stin_cd):
    """엘리베이터 이동 정보"""
    return _call_kric(
        "trafficWeekInfo", "stinElevatorMovement",
        railOprIsttCd=rail_op_cd, lnCd=ln_cd, stinCd=stin_cd,
    )


def get_transfer_movement(rail_op_cd, ln_cd, stin_cd):
    """환승 이동 (환승역만)"""
    return _call_kric(
        "vulnerableUserInfo", "transferMovement",
        railOprIsttCd=rail_op_cd, lnCd=ln_cd, stinCd=stin_cd,
    )


def get_wheelchair_lift(rail_op_cd, ln_cd, stin_cd):
    """휠체어 리프트 위치 (해당 시설 있는 역만)"""
    return _call_kric(
        "vulnerableUserInfo", "stationWheelchairLiftLocation",
        railOprIsttCd=rail_op_cd, lnCd=ln_cd, stinCd=stin_cd,
    )
