"""경로 카드 컴포넌트 - ODsay 데이터 대응"""

import streamlit as st
from components.styles import FONT_SIZE_PRESETS


def render_route_card(route, key_prefix=""):
    """경로 정보 카드 렌더링"""

    level = st.session_state.get("font_size_level", "보통")
    f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])
    fs_body = f["body"]
    fs_small = max(fs_body - 4, 12)
    fs_big = f["h2"]

    path_type = route.get("path_type", 0)
    type_icon = {1: "🚇", 2: "🚌", 3: "🚌🚇"}.get(path_type, "🚌")
    border_color = "#1f77b4" if path_type == 2 else "#2DB400" if path_type == 1 else "#6a5acd"

    payment = route.get("payment", 0)
    total_walk = route.get("total_walk", 0)

    st.markdown(
        f'<div style="background:white;border:2px solid {border_color};border-radius:16px;padding:20px;margin-bottom:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<span style="font-size:{fs_big}px;font-weight:bold;">{route["total_minutes"]}분</span>'
        f'<span style="font-size:{fs_small}px;color:#666;">환승 {route["transfers"]}회</span>'
        f'</div>'
        f'<div style="font-size:{fs_body}px;margin-bottom:8px;color:#333;">{type_icon} {route["summary"]}</div>'
        f'<div style="font-size:{fs_small}px;color:#666;margin-bottom:8px;">💰 {payment:,}원 · 🚶 도보 {total_walk}m</div>'
        f'<div style="background:#f0f7ff;padding:10px 14px;border-radius:8px;font-size:{fs_body}px;margin-top:8px;">'
        f'🚌 <b>{route["low_floor_bus_no"]}</b>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("이 경로로 안내받기 →", key=f"{key_prefix}_route_{route['id']}", use_container_width=True):
        st.session_state["selected_route_id"] = route["id"]
        st.session_state["odsay_routes"] = st.session_state.get("odsay_routes", [])
        st.switch_page("pages/2_경로_상세.py")
