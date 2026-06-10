"""지하철 진입/하차 출구 추론 — ODsay step 흐름 + 카카오 출구 좌표 기반."""
import re
from services.kakao_local import find_station_exits

# 출구 좌표 캐시 (프로세스 전역)
_exits_cache = {}


def _cached_station_exits(station_name):
    if station_name in _exits_cache:
        return _exits_cache[station_name]
    exits = find_station_exits(station_name) or {}
    _exits_cache[station_name] = exits
    return exits


def _nearest_exit(station_name, lng, lat, allowed=None):
    """타겟 좌표에 가장 가까운 출구 번호. allowed(접근가능 출구 집합) 주어지면 그 안에서만."""
    allowed = {str(a) for a in allowed} if allowed else None
    exits = _cached_station_exits(station_name)
    if not exits:
        if allowed:
            return sorted(allowed, key=lambda x: int(x))[0]
        return None
    cand = exits
    if allowed:
        cand = {no: c for no, c in exits.items() if str(no) in allowed}
        if not cand:
            return sorted(allowed, key=lambda x: int(x))[0]
    if lng is None or lat is None:
        if allowed:
            return sorted(allowed, key=lambda x: int(x))[0]
        return None
    best_no, best_d = None, float("inf")
    for no, (ex_lng, ex_lat) in cand.items():
        try:
            d = (float(ex_lng) - float(lng)) ** 2 + (float(ex_lat) - float(lat)) ** 2
        except (TypeError, ValueError):
            continue
        if d < best_d:
            best_d, best_no = d, no
    return best_no


def _same_station(a, b):
    """역명 정규화 비교 (괄호 부가명·'역' 접미사·공백 제거)."""
    def _norm(x):
        x = (x or "").split("(")[0].strip()
        if x.endswith("역"):
            x = x[:-1]
        return x.strip()
    a, b = _norm(a), _norm(b)
    return bool(a) and a == b


def infer_subway_exits(steps, origin_coord=None, dest_coord=None, accessible_map=None):
    """경로 step 흐름에서 각 지하철역의 진입/하차 출구 추론.
    Returns: {station_name: {"in": "7번", "out": "10번"}}
    """
    result = {}
    for i, s in enumerate(steps):
        if s.get("type") != "subway":
            continue
        st_name = s.get("start_name", "")
        end_name = s.get("end_name", "")
        if not st_name:
            continue
        # 역 내 환승 감지
        _prev_transit = None
        for j in range(i - 1, -1, -1):
            if steps[j].get("type") in ("subway", "bus"):
                _prev_transit = steps[j]
                break
        _next_transit = None
        for j in range(i + 1, len(steps)):
            if steps[j].get("type") in ("subway", "bus"):
                _next_transit = steps[j]
                break
        internal_in = bool(
            _prev_transit and _prev_transit.get("type") == "subway"
            and _same_station(_prev_transit.get("end_name", ""), st_name)
        )
        internal_out = bool(
            _next_transit and _next_transit.get("type") == "subway"
            and _same_station(_next_transit.get("start_name", ""), end_name)
        )
        # 진입 좌표
        in_lng = in_lat = None
        in_exit_from_name = None
        for j in range(i - 1, -1, -1):
            ps = steps[j]
            if ps.get("type") == "walk":
                # 진입: 도보의 '끝점'(역에 닿는 지점)이 실제 들어가는 출구.
                # start(걸어온 출발지)를 쓰면 반대편 출구가 잡힘.
                if ps.get("end_x") and ps.get("end_y"):
                    in_lng, in_lat = ps["end_x"], ps["end_y"]
                    m = re.search(r"(\d+)번\s*출구", ps.get("end_name", "") or "")
                    if m:
                        in_exit_from_name = f"{m.group(1)}번"
                    break
            else:
                if ps.get("end_x") and ps.get("end_y"):
                    in_lng, in_lat = ps["end_x"], ps["end_y"]
                    m = re.search(r"(\d+)번\s*출구", ps.get("end_name", "") or "")
                    if m:
                        in_exit_from_name = f"{m.group(1)}번"
                    break
        if in_lng is None and origin_coord:
            in_lng = origin_coord.get("lng")
            in_lat = origin_coord.get("lat")
        _allowed_in = accessible_map.get(st_name) if accessible_map else None
        if _allowed_in and in_exit_from_name:
            _mn = re.search(r"\d+", in_exit_from_name)
            if _mn and _mn.group() not in {str(a) for a in _allowed_in}:
                in_exit_from_name = None
        if in_exit_from_name and not internal_in:
            result.setdefault(st_name, {})["in"] = in_exit_from_name
        elif ((in_lng and in_lat) or _allowed_in) and not internal_in:
            no = _nearest_exit(st_name, in_lng, in_lat, allowed=_allowed_in)
            if no:
                result.setdefault(st_name, {})["in"] = f"{no}번"

        # 하차 좌표
        if end_name:
            out_lng = out_lat = None
            out_exit_from_name = None
            for j in range(i + 1, len(steps)):
                ns = steps[j]
                if ns.get("type") == "walk":
                    # 하차: 도보의 '시작점'(역에서 나오는 지점)이 실제 나가는 출구.
                    if ns.get("start_x") and ns.get("start_y"):
                        out_lng, out_lat = ns["start_x"], ns["start_y"]
                        m = re.search(r"(\d+)번\s*출구", ns.get("start_name", "") or "")
                        if m:
                            out_exit_from_name = f"{m.group(1)}번"
                        break
                else:
                    if ns.get("start_x") and ns.get("start_y"):
                        out_lng, out_lat = ns["start_x"], ns["start_y"]
                        m = re.search(r"(\d+)번\s*출구", ns.get("start_name", "") or "")
                        if m:
                            out_exit_from_name = f"{m.group(1)}번"
                        break
            if out_lng is None and dest_coord:
                out_lng = dest_coord.get("lng")
                out_lat = dest_coord.get("lat")
            _allowed_out = accessible_map.get(end_name) if accessible_map else None
            if _allowed_out and out_exit_from_name:
                _mo = re.search(r"\d+", out_exit_from_name)
                if _mo and _mo.group() not in {str(a) for a in _allowed_out}:
                    out_exit_from_name = None
            if out_exit_from_name and not internal_out:
                result.setdefault(end_name, {})["out"] = out_exit_from_name
            elif ((out_lng and out_lat) or _allowed_out) and not internal_out:
                no = _nearest_exit(end_name, out_lng, out_lat, allowed=_allowed_out)
                if no:
                    result.setdefault(end_name, {})["out"] = f"{no}번"
    return result
