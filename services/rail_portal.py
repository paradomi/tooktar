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


def _norm_line_name(name):
    """노선명 정규화: '수도권 수인.분당선' → '수인분당', '1호선' → '1호'."""
    return (name or "").replace("수도권", "").replace(" ", "").replace(".", "").replace("선", "").strip()


def find_station_codes_on_line(station_name: str, line_name: str):
    """역명 + 노선명으로 정확한 (railOprIsttCd, lnCd, stinCd, 역명) 반환.

    환승역(같은 역명이 여러 노선에 존재)에서 올바른 노선의 역코드를 고른다.
    예: 이매 → 경강선 'K411' vs 수인분당선 'K227(이매(성남아트센터))'.

    - line_name이 비었거나 CSV에 해당 노선이 없으면 find_station_codes로 fallback.
    - 노선은 찾았지만 그 노선에 해당 역이 없으면 None (잘못된 노선 정보 방지).
    """
    if not station_name:
        return None
    target_line = _norm_line_name(line_name)
    if not target_line:
        return find_station_codes(station_name)

    df = _load_station_codes()
    if df is None or df.empty:
        return None

    name = station_name.strip()
    if name.endswith("역"):
        name = name[:-1]

    # 노선 필터 (정규화 비교)
    line_mask = df["LN_NM"].apply(lambda x: _norm_line_name(str(x)) == target_line)
    sub = df[line_mask]
    if sub.empty:
        # CSV에 해당 노선명이 없음 → 기존 동작
        return find_station_codes(station_name)

    exact = sub[sub["STIN_NM"] == name]
    if not exact.empty:
        row = exact.iloc[0]
    else:
        partial = sub[sub["STIN_NM"].str.startswith(name, na=False)]
        if partial.empty:
            return None  # 이 노선에 해당 역 없음 → 잘못된 정보 표시 방지
        row = partial.iloc[0]
    return (
        str(row["RAIL_OPR_ISTT_CD"]),
        str(row["LN_CD"]),
        str(row["STIN_CD"]),
        str(row["STIN_NM"]),
    )


def _stin_cd_of(df, line_cd, station_name):
    """노선코드 + 역명으로 STIN_CD 반환. 부분매칭 허용."""
    if df is None or df.empty:
        return None
    sub = df[df["LN_CD"] == line_cd]
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    exact = sub[sub["STIN_NM"] == nm]
    if not exact.empty:
        return exact.iloc[0]["STIN_CD"]
    partial = sub[sub["STIN_NM"].str.startswith(nm, na=False)]
    if not partial.empty:
        return partial.iloc[0]["STIN_CD"]
    return None


def _stin_num(stin_cd):
    import re
    if not stin_cd:
        return None
    m = re.search(r"(\d+)", str(stin_cd))
    return int(m.group(1)) if m else None


def _line_terminals(df, line_cd):
    if df is None or df.empty:
        return None, None
    sub = df[df["LN_CD"] == line_cd]
    if sub.empty:
        return None, None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None, None
    pairs.sort(key=lambda p: p[0])
    return pairs[0][1], pairs[-1][1]


def _line_cd_of_station(df, station_name):
    if df is None or df.empty:
        return None
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    rows = df[df["STIN_NM"] == nm]
    if rows.empty:
        rows = df[df["STIN_NM"].str.startswith(nm, na=False)]
    if rows.empty:
        return None
    return str(rows.iloc[0]["LN_CD"])


def _adjacent_station(df, line_cd, start_num, direction):
    if df is None or df.empty:
        return None
    sub = df[df["LN_CD"] == line_cd]
    if sub.empty:
        return None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None
    pairs.sort(key=lambda p: p[0])
    nums = [p[0] for p in pairs]
    if start_num not in nums:
        return None
    idx = nums.index(start_num)
    nxt = idx + direction
    if 0 <= nxt < len(pairs):
        return pairs[nxt][1]
    return None


def direction_label(start_name, end_name, line_name=None):
    """ODsay subway step의 (start_name, end_name)으로 '(종점, 인접역) 방면' 라벨 생성.
    실패 시 '{end_name} 방면' fallback. line_name 주면 환승역 노선 정확히 매칭."""
    fallback = f"{end_name} 방면"
    if not start_name or not end_name:
        return fallback
    df = _load_station_codes()
    ln_cd = None
    if line_name:
        c = find_station_codes_on_line(start_name, line_name)
        if c:
            ln_cd = c[1]
    if not ln_cd:
        ln_cd = _line_cd_of_station(df, start_name)
    if not ln_cd:
        return fallback
    start_num = _stin_num(_stin_cd_of(df, ln_cd, start_name))
    end_num = _stin_num(_stin_cd_of(df, ln_cd, end_name))
    if start_num is None or end_num is None or start_num == end_num:
        return fallback
    direction = -1 if end_num < start_num else 1
    t_low, t_high = _line_terminals(df, ln_cd)
    terminal = t_low if direction == -1 else t_high
    adj = _adjacent_station(df, ln_cd, start_num, direction)
    if terminal and adj and terminal != adj:
        return f"({terminal}, {adj}) 방면"
    if terminal:
        return f"{terminal} 방면"
    return fallback


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
