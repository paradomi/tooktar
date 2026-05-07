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

if st.button("← 뒤로", key="back_home"):
    st.switch_page("app.py")

render_header()

origin_text = st.session_state.get("origin_input", "수원시청")
destination = st.session_state.get("selected_destination", "")

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

sort_option = st.radio(
    "정렬",
    ["최단 시간", "최소 환승"],
    horizontal=True,
    label_visibility="collapsed",
)

st.write("")

if sort_option == "최단 시간":
    routes = sorted(routes, key=lambda r: r["total_minutes"])
else:
    routes = sorted(routes, key=lambda r: r["transfers"])

for route in routes:
    render_route_card(route, key_prefix=sort_option)
