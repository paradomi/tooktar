"""KRIC 역사별 운행시각표(convenientInfo/stationTimetable) — 다음 열차 N분 후."""

import os
import functools
import datetime
import requests
import pandas as pd

KRIC_TIMETABLE_URL = "https://openapi.kric.go.kr/openapi/convenientInfo/stationTimetable"


def _get_api_key():
    """KRIC_TIMETABLE 우선, 없으면 KRIC fallback."""
    return os.getenv("KRIC_TIMETABLE") or os.getenv("KRIC", "")


def _get_day_code(ref_dt=None):
    """영업일 기준 dayCd. ref_dt 없으면 now() 사용.
    새벽 3시 이전이면 전날 영업일(weekday-1)로 보정.
    """
    if ref_dt is None:
        ref_dt = datetime.datetime.now()
    biz_date = ref_dt
    if ref_dt.hour < 3:
        biz_date = ref_dt - datetime.timedelta(days=1)
    wd = biz_date.weekday()
    if wd == 5:
        return "7"
    elif wd == 6:
        return "9"
    else:
        return "8"


def _parse_time_field(time_str, base_date):
    """HHMMSS 또는 HHMM 형식 시각 문자열을 datetime으로 변환.
    24~28시 익일 표기 처리. 실패 시 None 반환.
    """
    if not time_str:
        return None
    s = str(time_str).strip().replace(":", "")
    try:
        if len(s) >= 6:
            h = int(s[0:2])
            m = int(s[2:4])
        elif len(s) == 4:
            h = int(s[0:2])
            m = int(s[2:4])
        else:
            return None
        if h >= 24:
            # 익일 표기 (예: 25:30 → 다음날 01:30)
            next_day = base_date + datetime.timedelta(days=1)
            return next_day.replace(hour=h - 24, minute=m, second=0, microsecond=0)
        return base_date.replace(hour=h, minute=m, second=0, microsecond=0)
    except Exception:
        return None


@functools.lru_cache(maxsize=1)
def _build_stin_name_map():
    """data/station_codes.csv 를 한 번만 로드해 {STIN_CD: STIN_NM} dict 반환."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "station_codes.csv",
    )
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        return dict(zip(df["STIN_CD"].astype(str), df["STIN_NM"].astype(str)))
    except Exception:
        return {}


@functools.lru_cache(maxsize=64)
def _build_line_index(rail_op_cd, ln_cd):
    """노선의 역코드 순서 인덱스를 반환. {STIN_CD: int} 형태.

    STIN_CD 오름차순으로 정렬해 인덱스 부여. 캐싱으로 반복 호출 최적화.
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "station_codes.csv",
    )
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        mask = (df["RAIL_OPR_ISTT_CD"].astype(str) == str(rail_op_cd)) & \
               (df["LN_CD"].astype(str) == str(ln_cd))
        subset = df[mask].copy()
        subset = subset.sort_values("STIN_CD")
        return {str(row.STIN_CD): idx for idx, row in enumerate(subset.itertuples())}
    except Exception:
        return {}


def _stin_cd_to_name(stin_cd):
    """역코드를 역명으로 변환. 매핑 실패 시 코드 그대로 반환."""
    mapping = _build_stin_name_map()
    return mapping.get(str(stin_cd), str(stin_cd))


def get_next_trains(rail_op_cd, ln_cd, stin_cd, limit=3, window_min=120, to_stin_cd=None):
    """KRIC 시각표 기반 다음 열차 조회.

    Args:
        rail_op_cd: 운영기관코드 (예: KR=한국철도공사)
        ln_cd: 노선코드 (예: K1=수인분당)
        stin_cd: 역코드 (예: K243=수원시청)
        limit: 최대 반환 열차 수
        window_min: 현재 시각 기준 N분 이내 출발 열차만
        to_stin_cd: 내릴 역의 STIN_CD. 주어지면 해당 방향 열차만 필터링. None이면 필터 없음.

    Returns:
        dict: {
            "trains": list[dict],  # [{"minutes_until": int, "destination": str, "train_no": str}, ...]
            "last_dpt": str|None,  # 방향 필터 적용 후 가장 늦은 출발 시각 "HH:MM" or None
            "status": str,         # "ok" | "after_last" | "no_data"
        }
    """
    _empty = {"trains": [], "last_dpt": None, "status": "no_data"}

    if not rail_op_cd or not ln_cd or not stin_cd:
        return _empty

    api_key = _get_api_key()
    if not api_key:
        return _empty

    now = datetime.datetime.now()
    day_cd = _get_day_code(now)

    # 영업일 기준 자정을 base_date로 사용
    if now.hour < 3:
        biz_day = now - datetime.timedelta(days=1)
    else:
        biz_day = now
    base_date = biz_day.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        r = requests.get(
            KRIC_TIMETABLE_URL,
            params={
                "serviceKey": api_key,
                "format": "json",
                "dayCd": day_cd,
                "lnCd": ln_cd,
                "railOprIsttCd": rail_op_cd,
                "stinCd": stin_cd,
            },
            timeout=10,
        )
        if r.status_code != 200:
            return _empty

        try:
            data = r.json()
        except Exception:
            return _empty

        header = data.get("header", {})
        if header.get("resultCode") != "00":
            return _empty

        items = data.get("body", [])
        if not items or not isinstance(items, list):
            return _empty

        # 방향 필터링용 노선 인덱스 (to_stin_cd가 있고 승차역 != 하차역일 때만 사용)
        use_direction_filter = (
            to_stin_cd is not None
            and str(to_stin_cd) != str(stin_cd)
        )
        line_index = _build_line_index(rail_op_cd, ln_cd) if use_direction_filter else {}
        idx_board = line_index.get(str(stin_cd))
        idx_alight = line_index.get(str(to_stin_cd)) if to_stin_cd else None

        # 방향 필터링 적용 후 전체 열차 목록 (시간 필터 미적용)
        direction_filtered = []
        for item in items:
            dpt_tm = item.get("dptTm") or item.get("arvTm")
            dt = _parse_time_field(dpt_tm, base_date)
            if dt is None:
                continue

            dest_cd = item.get("tmnStinCd", "")
            destination = _stin_cd_to_name(dest_cd) if dest_cd else ""

            # 방향 필터링: 내릴 역이 승차역~종착역 사이에 있어야 통과
            if use_direction_filter and idx_board is not None and idx_alight is not None:
                if dest_cd:
                    idx_tmn = line_index.get(str(dest_cd))
                    if idx_tmn is not None:
                        lo = min(idx_board, idx_tmn)
                        hi = max(idx_board, idx_tmn)
                        if not (lo <= idx_alight <= hi):
                            continue
                    # idx_tmn 못 찾으면 graceful: 그냥 통과

            direction_filtered.append({
                "dt": dt,
                "destination": destination,
                "train_no": str(item.get("trnNo", "")),
                "dpt_tm_raw": str(dpt_tm) if dpt_tm else "",
            })

        # 막차: 방향 필터 적용 후 가장 늦은 출발 시각
        last_dpt = None
        if direction_filtered:
            latest = max(direction_filtered, key=lambda x: x["dt"])
            raw = latest["dpt_tm_raw"].strip().replace(":", "")
            try:
                if len(raw) >= 4:
                    h = int(raw[0:2])
                    m = int(raw[2:4])
                    last_dpt = f"{h:02d}:{m:02d}"
            except Exception:
                pass

        # 시간 필터 적용 → trains 계산
        results = []
        for entry in direction_filtered:
            dt = entry["dt"]
            diff_sec = (dt - now).total_seconds()
            diff_min = diff_sec / 60
            if diff_min < -1 or diff_min > window_min:
                continue
            results.append({
                "minutes_until": max(0, int(round(diff_min))),
                "destination": entry["destination"],
                "train_no": entry["train_no"],
                "dpt_iso": dt.isoformat(),  # 캐시 후 시간 재계산용 절대시각
            })

        results.sort(key=lambda x: x["minutes_until"])
        trains = results[:limit]

        if trains:
            status = "ok"
        elif direction_filtered:
            status = "after_last"
        else:
            status = "no_data"

        return {"trains": trains, "last_dpt": last_dpt, "status": status}

    except Exception:
        return _empty
