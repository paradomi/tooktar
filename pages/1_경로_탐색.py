"""경로 탐색 결과 화면 - ODsay 실제 API 연동"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.styles import apply_global_styles
from components.header import render_header
from components.route_card import render_route_card
from services.geocode import address_to_coord
from services.odsay_api import search_pub_trans_path, parse_routes

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

if st.button("← 뒤로", key="back_home"):
    st.switch_page("app.py")

render_header()

origin_text = st.session_state.get("origin_input", "수원시청")
destination = st.session_state.get("selected_destination", "")

# 출발지/도착지 텍스트가 바뀌면 캐시된 좌표를 무효화 (자주가는곳 버튼으로 새 도착지 진입 시 반영)
if st.session_state.get("_prev_destination") != destination:
    st.session_state.pop("dest_coord", None)
    st.session_state["_prev_destination"] = destination
if st.session_state.get("_prev_origin") != origin_text:
    st.session_state.pop("origin_coord", None)
    st.session_state["_prev_origin"] = origin_text

st.markdown(f"### 🎯 {origin_text} → {destination}")

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
    # 휠체어 모드: 도보 짧은 순 → 환승 적은 순 → 시간 짧은 순
    routes = sorted(routes, key=lambda r: (r.get("total_walk", 0), r.get("transfers", 0), r["total_minutes"]))
elif current_mode == "walk_less":
    # 덜 걷는 길: 도보 짧은 순 → 시간 짧은 순
    routes = sorted(routes, key=lambda r: (r.get("total_walk", 0), r["total_minutes"]))
else:
    # 빠른 길: 시간 짧은 순
    routes = sorted(routes, key=lambda r: r["total_minutes"])

for route in routes:
    render_route_card(route, key_prefix=f"route_{current_mode}")
