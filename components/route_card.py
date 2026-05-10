"""경로 카드 (HTML 디자인 + Streamlit 버튼)"""
import streamlit as st

NAVY = "#002F6C"


def render_route_card(route, key_prefix="", lf_score=None):
    path_type = route.get("path_type", 0)
    type_icon = {1: "🚇", 2: "🚌", 3: "🚌🚇"}.get(path_type, "🚌")
    payment = route.get("payment", 0)
    total_walk = route.get("total_walk", 0)
    route_id = route.get("id", 0)

    # 저상버스 점수 배지 (휠체어 모드에서만 전달됨)
    lf_badge = ""
    if lf_score is not None:
        if lf_score >= 1.0:
            lf_badge = (
                f'<span style="background:{NAVY};color:white;font-size:0.75rem;'
                f'font-weight:700;padding:3px 10px;border-radius:10px;'
                f'margin-left:8px;vertical-align:middle;">♿ 저상 도착 가능</span>'
            )
        elif lf_score > 0:
            pct = int(lf_score * 100)
            lf_badge = (
                f'<span style="background:#FFA726;color:white;font-size:0.75rem;'
                f'font-weight:700;padding:3px 10px;border-radius:10px;'
                f'margin-left:8px;vertical-align:middle;">♿ 일부 ({pct}%)</span>'
            )
        else:
            lf_badge = (
                f'<span style="background:#999;color:white;font-size:0.75rem;'
                f'font-weight:700;padding:3px 10px;border-radius:10px;'
                f'margin-left:8px;vertical-align:middle;">♿ 저상 미도착</span>'
            )

    st.markdown(
        f'''
        <div style="
            border: 2px solid {NAVY};
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 8px;
            background: white;
            transition: transform 0.15s, box-shadow 0.15s;
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:2rem;font-weight:700;color:{NAVY};">{route['total_minutes']}분{lf_badge}</span>
                <span style="font-size:0.95rem;color:#666;">환승 {route['transfers']}회</span>
            </div>
            <div style="font-size:1.1rem;color:#333;margin-bottom:4px;">{type_icon} {route['summary']}</div>
            <div style="font-size:0.9rem;color:#666;margin-bottom:12px;">💰 {payment:,}원 · 🚶 도보 {total_walk}m</div>
            <div style="background:rgba(0,47,108,0.06);border-radius:10px;padding:10px 14px;">
                <span style="font-size:1rem;font-weight:700;color:{NAVY};">🚌 {route['low_floor_bus_no']}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    if st.button(
        "이 경로로 안내받기 →",
        key=f"{key_prefix}_route_{route_id}",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["selected_route_id"] = route_id
        st.session_state["odsay_routes"] = st.session_state.get("odsay_routes", [])
        st.switch_page("pages/2_경로_상세.py")
