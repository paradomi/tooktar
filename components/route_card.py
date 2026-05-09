"""경로 카드 컴포넌트"""

import streamlit as st
from components.styles import FONT_SIZE_PRESETS


def render_route_card(route, key_prefix=""):
    """경로 정보 카드 렌더링"""

    level = st.session_state.get("font_size_level", "보통")
    f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])
    fs_body = f["body"]
    fs_small = max(fs_body - 4, 12)
    fs_big = f["h2"]

    # 단차 없는 경로는 강조
    border_color = "#1f77b4" if route["is_step_free"] else "#999"
    bg_color = "#f0f7ff" if route["is_step_free"] else "white"
    badge = "🟢 단차 없음" if route["is_step_free"] else "🟡 경사로 있음"

    st.markdown(
        f'<div style="background:{bg_color};border:2px solid {border_color};border-radius:16px;padding:20px;margin-bottom:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<span style="font-size:{fs_big}px;font-weight:bold;">{route["total_minutes"]}분</span>'
        f'<span style="font-size:{fs_small}px;color:#666;">환승 {route["transfers"]}회</span>'
        f'</div>'
        f'<div style="font-size:{fs_body}px;margin-bottom:8px;color:#333;">{route["summary"]}</div>'
        f'<div style="font-size:{fs_small}px;margin-bottom:8px;">{badge} · 휠체어 지수 <b>{route["barrier_free_score"]}</b></div>'
        f'<div style="background:#fff8dc;padding:10px 14px;border-radius:8px;font-size:{fs_body}px;margin-top:8px;">'
        f'🚌 <b>저상 {route["low_floor_bus_no"]}번</b> · {route["low_floor_arrival"]}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 클릭 버튼 (Streamlit 한계상 카드 자체 클릭은 불가, 아래 버튼으로 대체)
    if st.button(f"이 경로로 안내받기 →", key=f"{key_prefix}_route_{route['id']}", use_container_width=True):
        st.session_state["selected_route_id"] = route["id"]
        st.switch_page("pages/2_경로_상세.py")