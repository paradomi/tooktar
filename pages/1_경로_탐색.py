"""경로 탐색 결과 화면 - ODsay 실제 API 연동"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.styles import apply_global_styles
from components.header import render_header
from components.route_card import render_route_card
from services.geocode import address_to_coord
from services.odsay_api import search_pub_trans_path, parse_routes

NAVY = "#002F6C"

st.set_page_config(page_title="경로 탐색", page_icon="🚌", layout="centered")

apply_global_styles()

st.markdown("""
<style>
/* st.columns(3) 모바일에서도 가로 3분할 유지 */
[data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 6px !important;
}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 0 !important;
}
/* 모드 카드 — viewport 반응형, 데스크톱·모바일 모두 자연스럽게 */
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) {
    min-height: 110px;
    max-height: 160px;
    aspect-ratio: 1 / 1.05;
    white-space: pre-line;
    line-height: 1.1;
    padding: 10px 6px;
    gap: 0.3rem;
}
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) p {
    margin: 0;
    font-size: clamp(2rem, 9vw, 3rem);
    line-height: 1;
}
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) strong {
    font-size: clamp(1.1rem, 4.8vw, 1.7rem);
    font-weight: 700;
}
/* 휠체어 맞춤(2번째 컬럼)은 글자가 길어 살짝 작게 */
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] > button:has(strong) strong {
    font-size: clamp(0.95rem, 4vw, 1.5rem);
}
</style>
""", unsafe_allow_html=True)

render_header(back_target="app.py")

# 페이지 전환 플래그 처리
if st.session_state.get("_pending_nav"):
    target = st.session_state.pop("_pending_nav")
    st.switch_page(target)

origin_text = st.session_state.get("origin_input", "수원시청")
destination = st.session_state.get("selected_destination", "")

# 출발지/도착지 텍스트가 바뀌면 캐시된 좌표를 무효화 (자주가는곳 버튼으로 새 도착지 진입 시 반영)
if st.session_state.get("_prev_destination") != destination:
    st.session_state.pop("dest_coord", None)
    st.session_state["_prev_destination"] = destination
if st.session_state.get("_prev_origin") != origin_text:
    st.session_state.pop("origin_coord", None)
    st.session_state["_prev_origin"] = origin_text

st.markdown(
    f'<div style="background:rgba(0,47,108,0.06);border-radius:12px;padding:12px 16px;margin-bottom:16px;">'
    f'<div style="font-size:1.05rem;font-weight:700;color:{NAVY};">🎯 {origin_text} → {destination}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── ODsay 경로 검색 ───
routes = []
api_error = False

if destination.strip():
    origin_coord = st.session_state.get("origin_coord")
    dest_coord = st.session_state.get("dest_coord")

    if not origin_coord:
        clean_origin = origin_text.replace("📍 현재 위치 (", "").replace(")", "").strip()
        origin_coord = address_to_coord(clean_origin)
        if origin_coord:
            st.session_state["origin_coord"] = origin_coord

    if not dest_coord:
        dest_coord = address_to_coord(destination)
        if dest_coord:
            st.session_state["dest_coord"] = dest_coord

    if origin_coord and dest_coord:
        cache_key = f"odsay_{origin_coord['lng']}_{origin_coord['lat']}_{dest_coord['lng']}_{dest_coord['lat']}"
        if cache_key in st.session_state:
            routes = st.session_state[cache_key]
            st.session_state["odsay_routes"] = routes
        else:
            with st.spinner("🔍 대중교통 경로를 검색하고 있습니다..."):
                result = search_pub_trans_path(
                    sx=origin_coord["lng"], sy=origin_coord["lat"],
                    ex=dest_coord["lng"], ey=dest_coord["lat"],
                )
            if result:
                routes = parse_routes(result)
                st.session_state[cache_key] = routes
                st.session_state["odsay_routes"] = routes
            else:
                api_error = True
    else:
        api_error = True

if api_error:
    st.warning("경로를 검색할 수 없습니다. 출발지/도착지를 다시 확인해주세요.")

if not routes:
    if not api_error:
        st.info("검색 결과가 없습니다.")
    st.stop()

st.caption(f"총 {len(routes)}개 경로를 찾았습니다")
st.write("")

# ─── 경로 유형 선택 (UI만 — 로직 미적용) ───
ROUTE_MODES = [
    {"key": "fast",      "icon": "🚀", "name": "빠른 길",      "sub": "기본",       "desc": "일반적인 최단 시간 경로"},
    {"key": "wheel",     "icon": "♿", "name": "휠체어 맞춤",  "sub": "단차 없음",  "desc": "저상버스 필수, 계단 제외 보행, 엘리베이터 출구 안내"},
    {"key": "walk_less", "icon": "🚶", "name": "덜 걷는 길",   "sub": "고령자 맞춤", "desc": "도보 최소화, 최소 환승, 평지 위주 경로"},
]

if "route_mode" not in st.session_state:
    st.session_state["route_mode"] = "fast"

current_mode = st.session_state["route_mode"]

mode_cols = st.columns(3)
for i, opt in enumerate(ROUTE_MODES):
    with mode_cols[i]:
        is_selected = current_mode == opt["key"]
        if st.button(
            f"{opt['icon']}\n\n**{opt['name']}**",
            key=f"mode_{opt['key']}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state["route_mode"] = opt["key"]
            st.rerun()

selected_opt = next(o for o in ROUTE_MODES if o["key"] == current_mode)
if current_mode == "wheel":
    st.markdown(
        f'<div style="background:#f3e5f5;border-left:4px solid #7B1FA2;'
        f'padding:10px 14px;border-radius:8px;margin-top:8px;color:#4A148C;font-weight:600;">'
        f'♿ {selected_opt["desc"]}</div>',
        unsafe_allow_html=True,
    )
else:
    st.caption(f"💡 {selected_opt['desc']}")

st.write("")

# ─── 공통: 모든 모드에서 버스 도착 정보 조회 ───
from services.bus_arrival import get_arrivals as _wheel_get_arrivals
from services.bus_arrival import has_low_floor_arriving as _wheel_has_lf
from concurrent.futures import ThreadPoolExecutor

LF_WINDOW_MIN = 30


def _stop_key(s):
    return f"gbis_arr_{s.get('start_id')}_{s.get('start_x')}_{s.get('start_y')}"


def _fetch_arrivals(step):
    return _wheel_get_arrivals(
        station_id=step.get("start_id"),
        lng=step.get("start_x"), lat=step.get("start_y"),
        city_code_hint=step.get("city_code"),
        station_name=step.get("start_name", ""),
    )


# 모든 bus step 수집 + 정류장별 dedup (한 번만)
_all_bus_steps = []
for r in routes:
    for s in r.get("steps", []):
        if s.get("type") == "bus":
            _all_bus_steps.append(s)

_seen_keys = set()
_to_fetch = []
for s in _all_bus_steps:
    k = _stop_key(s)
    if k in _seen_keys:
        continue
    _seen_keys.add(k)
    if k not in st.session_state:
        _to_fetch.append((k, s))

if _to_fetch:
    _spinner_msg = (
        f"♿ 저상버스 실시간 도착 정보 확인 중... ({len(_to_fetch)}개 정류장)"
        if current_mode == "wheel"
        else f"🚌 버스 실시간 도착 정보 확인 중... ({len(_to_fetch)}개 정류장)"
    )
    with st.spinner(_spinner_msg):
        _workers = min(max(len(_to_fetch), 1), 12)
        with ThreadPoolExecutor(max_workers=_workers) as ex:
            _results = list(ex.map(lambda x: _fetch_arrivals(x[1]), _to_fetch))
        for (ck, _), res in zip(_to_fetch, _results):
            st.session_state[ck] = res or []


def _first_bus_arrival(route):
    """경로의 첫 bus step의 다음 도착 정보."""
    for s in route.get("steps", []):
        if s.get("type") != "bus":
            continue
        bus_no = s.get("bus_no", "")
        arrivals = st.session_state.get(_stop_key(s), [])
        matched = [a for a in (arrivals or []) if a.get("route_name") == bus_no]
        if not matched:
            return None
        preds = matched[0].get("predictions", [])
        if not preds:
            return None
        p = preds[0]
        return {
            "bus_no": bus_no,
            "minutes": p.get("minutes"),
            "low_floor": p.get("low_floor", False),
            "stops_left": p.get("stops_left"),
        }
    return None


def _first_bus_minutes(route):
    """첫 버스 도착까지 분. 정보 없으면 큰 값(맨 뒤로)."""
    info = _first_bus_arrival(route)
    if info and info.get("minutes") is not None:
        try:
            return int(info["minutes"])
        except (ValueError, TypeError):
            return 9999
    return 9999


def _arr_group(route):
    """실시간 버스 도착정보 있으면 0(위), 없으면 1(아래)."""
    return 0 if _first_bus_minutes(route) < 9999 else 1


if current_mode == "wheel":
    def _route_lf_score(route):
        rid = route.get("id", 0)
        score_ck = f"route_lf_score_v3_{cache_key}_{rid}"
        if score_ck in st.session_state:
            return st.session_state[score_ck]
        bus_steps = [s for s in route.get("steps", []) if s.get("type") == "bus"]
        if not bus_steps:
            st.session_state[score_ck] = "subway_only"
            return "subway_only"
        ok = 0
        data_steps = 0  # GBIS 데이터를 받은 step 수
        for s in bus_steps:
            bus_no = s.get("bus_no", "")
            arrivals = st.session_state.get(_stop_key(s), [])
            matched = [a for a in (arrivals or []) if a.get("route_name") == bus_no]
            has_data = bool(matched and matched[0].get("predictions"))
            step_ok = False
            # 1) 도착예정 첫 두 대 중 저상 (LF_WINDOW_MIN 이내)
            if matched:
                for p in matched[0].get("predictions", []):
                    m = p.get("minutes")
                    if p.get("low_floor") and m is not None and m <= LF_WINDOW_MIN:
                        step_ok = True
                        break
            # 2) 첫 두 대에 저상 없으면 노선 단위 위치 검증
            if not step_ok and bus_no:
                lf_ck = f"lf_loc_v3_{s.get('start_id') or 'no'}_{bus_no}"
                if lf_ck in st.session_state:
                    step_ok = st.session_state[lf_ck]
                else:
                    if s.get("start_id"):
                        step_ok = _wheel_has_lf(s.get("start_id"), bus_no, max_stops_ahead=15)
                    else:
                        from services.bus_arrival import has_low_floor_on_route as _route_check
                        step_ok = _route_check(bus_no)
                    st.session_state[lf_ck] = step_ok
                if step_ok:
                    has_data = True
            if has_data:
                data_steps += 1
                if step_ok:
                    ok += 1
        if data_steps == 0:
            # 모든 bus step의 GBIS 데이터를 받지 못함 → 미확인 (정렬상 1.0 동급)
            score = None
        else:
            score = ok / data_steps
        st.session_state[score_ck] = score
        return score

    # 기존에 _route_lf_score step 2에서 순차로 돌던 저상 위치 검증(GBIS 호출)을
    # 점수 계산 루프 전에 병렬로 미리 처리한다. 동일한 lf_ck 캐시 키에 결과를 채워
    # 이후 _route_lf_score는 캐시만 읽도록(네트워크 호출 0) 만든다.
    _lf_jobs = []
    _seen_lf_ck = set()
    for _r in routes:
        for s in _r.get("steps", []):
            if s.get("type") != "bus":
                continue
            bus_no = s.get("bus_no", "")
            if not bus_no:
                continue
            # step 1: 캐시된 도착정보로 저상 여부 판단 (네트워크 호출 없음)
            arrivals = st.session_state.get(_stop_key(s), [])
            matched = [a for a in (arrivals or []) if a.get("route_name") == bus_no]
            step1_ok = False
            if matched:
                for p in matched[0].get("predictions", []):
                    m = p.get("minutes")
                    if p.get("low_floor") and m is not None and m <= LF_WINDOW_MIN:
                        step1_ok = True
                        break
            if step1_ok:
                continue
            lf_ck = f"lf_loc_v3_{s.get('start_id') or 'no'}_{bus_no}"
            if lf_ck in st.session_state:
                continue
            if lf_ck in _seen_lf_ck:
                continue
            _seen_lf_ck.add(lf_ck)
            _lf_jobs.append((lf_ck, s.get("start_id"), bus_no))

    if _lf_jobs:
        def _check_lf(job):
            _ck, sid, bno = job
            if sid:
                return _wheel_has_lf(sid, bno, max_stops_ahead=15)
            from services.bus_arrival import has_low_floor_on_route as _route_check
            return _route_check(bno)

        _workers = min(max(len(_lf_jobs), 1), 8)
        with st.spinner("♿ 저상버스 운행 확인 중..."):
            with ThreadPoolExecutor(max_workers=_workers) as ex:
                _lf_results = list(ex.map(_check_lf, _lf_jobs))
        for (ck, _sid, _bno), val in zip(_lf_jobs, _lf_results):
            st.session_state[ck] = val

    scored = [(r, _route_lf_score(r)) for r in routes]

    def _lf_tier(s):
        """저상 정렬 티어. 작을수록 위쪽."""
        if s == 1.0 or s == "subway_only":
            return 0  # 확정 OK (저상 모두 도착 or 저상 이슈 없음)
        if isinstance(s, (int, float)) and s > 0:
            return 1  # 부분 저상
        if s is None:
            return 2  # 미확인 (버스 있지만 GBIS 데이터 없음)
        return 3      # 저상 없음 (score == 0)

    scored.sort(key=lambda x: (
        _lf_tier(x[1]),
        _arr_group(x[0]),            # 도착정보 없는 경로는 같은 티어 내 아래로
        _first_bus_minutes(x[0]),    # 버스 빨리 오는 순
        x[0]["total_minutes"],       # 도착 같으면 총시간 짧은 순 (긴 건 뒤로)
        x[0].get("total_walk", 0),
        x[0].get("transfers", 0),
    ))

    def _norm_score_for_card(s):
        return None if s == "subway_only" else s

    routes_with_scores = [
        (r, s, _first_bus_arrival(r)) for r, s in scored
    ]
    numeric_scores = [s for r, s in scored if isinstance(s, (int, float))]
    if numeric_scores and max(numeric_scores) < 1.0:
        st.info("⚠️ 30분 이내 저상버스가 도착하는 경로가 제한적입니다. 위쪽 경로일수록 휠체어 친화도가 높습니다.")
elif current_mode == "walk_less":
    # 도착정보 없는 경로는 아래로, 그 안에서 도보 짧은 순
    routes = sorted(routes, key=lambda r: (_arr_group(r), r.get("total_walk", 0), r["total_minutes"]))
    routes_with_scores = [(r, None, _first_bus_arrival(r)) for r in routes]
else:
    # 빠른 길: 버스 빨리 오는 순 우선, 도착정보 없는 경로는 맨 아래
    routes = sorted(routes, key=lambda r: (_first_bus_minutes(r), r["total_minutes"]))
    routes_with_scores = [(r, None, _first_bus_arrival(r)) for r in routes]

for item in routes_with_scores:
    if len(item) == 3:
        route, score, bus_arr = item
    else:
        route, score = item
        bus_arr = None
    render_route_card(
        route, key_prefix=f"route_{current_mode}",
        lf_score=_norm_score_for_card(score) if current_mode == "wheel" else score,
        bus_arrival=bus_arr,
    )
