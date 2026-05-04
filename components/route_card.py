"""경로 카드 컴포넌트"""

import streamlit as st

def render_route_card(route, key_prefix=""):
    """경로 정보 카드 렌더링"""
    
    # 단차 없는 경로는 강조
    border_color = "#1f77b4" if route["is_step_free"] else "#999"
    bg_color = "#f0f7ff" if route["is_step_free"] else "white"
    badge = "🟢 단차 없음" if route["is_step_free"] else "🟡 경사로 있음"
    
    st.markdown(f"""
    <div style="
        background: {bg_color};
        border: 2px solid {border_color};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 28px; font-weight: bold;">{route['total_minutes']}분</span>
            <span style="font-size: 14px; color: #666;">환승 {route['transfers']}회</span>
        </div>
        <div style="font-size: 16px; margin-bottom: 8px; color: #333;">
            {route['summary']}
        </div>
        <div style="font-size: 14px; margin-bottom: 8px;">
            {badge} · 배리어프리 지수 <b>{route['barrier_free_score']}</b>
        </div>
        <div style="
            background: #fff8dc;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 15px;
            margin-top: 8px;
        ">
            🚌 <b>저상 {route['low_floor_bus_no']}번</b> · {route['low_floor_arrival']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 클릭 버튼 (Streamlit 한계상 카드 자체 클릭은 불가, 아래 버튼으로 대체)
    if st.button(f"이 경로로 안내받기 →", key=f"{key_prefix}_route_{route['id']}", use_container_width=True):
        st.session_state["selected_route_id"] = route["id"]
        st.switch_page("pages/2_경로_상세.py")