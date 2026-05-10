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
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) {
    min-height: 140px;
    white-space: pre-line;
    line-height: 1.2;
    padding: 0.8rem 0.4rem;
    gap: 0.3rem;
}
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) p {
    margin: 0;
    font-size: 3rem;
    line-height: 1;
}
[data-testid="stMain"] [data-testid="stButton"] > button:has(strong) strong {
    font-size: 2rem;
    font-weight: 700;
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

if current_mode == "wheel":
    # 휠체어 모드: 정류장 단위 dedup + ThreadPoolExecutor 병렬 + session_state 캐시
    from services.bus_arrival import get_arrivals as _wheel_get_arrivals
    from concurrent.futures import ThreadPoolExecutor

    LF_WINDOW_MIN = 30

    def _stop_key(s):
        return f"gbis_arr_{s.get('start_id')}_{s.get('start_x')}_{s.get('start_y')}"

    def _fetch_arrivals(step):
        return _wheel_get_arrivals(
            station_id=step.get("start_id"),
            lng=step.get("start_x"), lat=step.get("start_y"),
            city_code_hint=step.get("city_code"),
        )

    # 모든 bus step 수집 + 정류장별 dedup
    all_bus_steps = []
    for r in routes:
        for s in r.get("steps", []):
            if s.get("type") == "bus":
                all_bus_steps.append(s)

    seen_keys = set()
    to_fetch = []  # 캐시 미보유 정류장만
    for s in all_bus_steps:
        k = _stop_key(s)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        if k not in st.session_state:
            to_fetch.append((k, s))

    if to_fetch:
        with st.spinner(f"♿ 저상버스 실시간 도착 정보 확인 중... ({len(to_fetch)}개 정류장)"):
            with ThreadPoolExecutor(max_workers=6) as ex:
                results = list(ex.map(lambda x: _fetch_arrivals(x[1]), to_fetch))
            for (ck, _), res in zip(to_fetch, results):
                st.session_state[ck] = res or []

    def _route_lf_score(route):
        rid = route.get("id", 0)
        score_ck = f"route_lf_score_v2_{cache_key}_{rid}"
        if score_ck in st.session_state:
            return st.session_state[score_ck]
        bus_steps = [s for s in route.get("steps", []) if s.get("type") == "bus"]
        if not bus_steps:
            st.session_state[score_ck] = None
            return None
        ok = 0
        for s in bus_steps:
            bus_no = s.get("bus_no", "")
            arrivals = st.session_state.get(_stop_key(s), [])
            for a in arrivals or []:
                if a.get("route_name") != bus_no:
                    continue
                for p in a.get("predictions", []):
                    m = p.get("minutes")
                    if p.get("low_floor") and m is not None and m <= LF_WINDOW_MIN:
                        ok += 1
                        break
                else:
                    continue
                break
        score = ok / len(bus_steps)
        st.session_state[score_ck] = score
        return score

    scored = [(r, _route_lf_score(r)) for r in routes]

    # bus 없는 경로(score=None)는 저상 이슈 없음 → 1.0 동급으로 정렬
    scored.sort(key=lambda x: (
        -(x[1] if x[1] is not None else 1.0),  # 저상 점수 내림차순
        x[0].get("total_walk", 0),              # 도보 짧은 순
        x[0].get("transfers", 0),               # 환승 적은 순
        x[0]["total_minutes"],                  # 시간 짧은 순
    ))
    routes_with_scores = scored

    # bus 있는 경로 중 100% 미달 케이스가 있으면 안내
    bus_routes_scores = [s for r, s in scored if s is not None]
    if bus_routes_scores and max(bus_routes_scores) < 1.0:
        st.info("⚠️ 30분 이내 저상버스가 도착하는 경로가 제한적입니다. 위쪽 경로일수록 휠체어 친화도가 높습니다.")
elif current_mode == "walk_less":
    # 덜 걷는 길: 도보 짧은 순 → 시간 짧은 순
    routes = sorted(routes, key=lambda r: (r.get("total_walk", 0), r["total_minutes"]))
    routes_with_scores = [(r, None) for r in routes]
else:
    # 빠른 길: 시간 짧은 순
    routes = sorted(routes, key=lambda r: r["total_minutes"])
    routes_with_scores = [(r, None) for r in routes]

for route, score in routes_with_scores:
    render_route_card(route, key_prefix=f"route_{current_mode}", lf_score=score)
