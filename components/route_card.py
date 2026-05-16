"""경로 카드 (HTML 디자인 + Streamlit 버튼)"""
import streamlit as st

NAVY = "#002F6C"


def _arrival_html_inline(bus_arrival, navy):
    """카드 안에 들어갈 도착 정보 HTML. bus_arrival None이면 빈 문자열."""
    if not bus_arrival:
        return ""
    bus_no = bus_arrival.get("bus_no", "")
    minutes = bus_arrival.get("minutes")
    low = bus_arrival.get("low_floor", False)
    stops = bus_arrival.get("stops_left")
    if minutes is None:
        return ""
    low_tag = (
        f'<span style="background:{navy};color:white;font-size:1.05rem;'
        f'font-weight:700;padding:3px 10px;border-radius:10px;margin-left:6px;">'
        f'♿저상</span>' if low else ""
    )
    stops_str = f" ({stops}정류장 전)" if stops else ""
    return (
        f'<div style="margin-top:8px;font-size:1.3rem;color:#222;font-weight:600;">'
        f'⏱️ <b>{minutes}분 후</b>{low_tag}{stops_str}</div>'
    )


def render_route_card(route, key_prefix="", lf_score=None, bus_arrival=None):
    """경로 카드.

    Args:
        route: 경로 dict
        key_prefix: 버튼 키 prefix
        lf_score: 저상버스 점수 (None=미적용, 0~1.0)
        bus_arrival: 첫 bus step 실시간 도착정보
            {"bus_no":"88", "minutes":22, "low_floor":True, "stops_left":"14"} or None
    """
    path_type = route.get("path_type", 0)
    type_icon = {1: "🚇", 2: "🚌", 3: "🚌🚇"}.get(path_type, "🚌")
    payment = route.get("payment", 0)
    total_walk = route.get("total_walk", 0)
    route_id = route.get("id", 0)

    # 저상버스 점수 배지 (휠체어 모드에서만 전달됨)
    # None = 데이터 부재 또는 bus 없음(지하철만) → 라벨 미표시
    lf_badge = ""
    if lf_score is not None:
        if lf_score >= 1.0:
            lf_badge = (
                f'<span style="background:{NAVY};color:white;font-size:1.1rem;'
                f'font-weight:700;padding:4px 12px;border-radius:12px;'
                f'margin-left:10px;vertical-align:middle;">♿ 저상 도착 가능</span>'
            )
        elif lf_score > 0:
            pct = int(lf_score * 100)
            lf_badge = (
                f'<span style="background:#FFA726;color:white;font-size:1.1rem;'
                f'font-weight:700;padding:4px 12px;border-radius:12px;'
                f'margin-left:10px;vertical-align:middle;">♿ 일부 ({pct}%)</span>'
            )
        # lf_score == 0 (저상 미도착 확정)인 경우는 라벨 없이 후순위로만 처리

    st.markdown(
        f'<div style="border:2px solid {NAVY};border-radius:20px;padding:20px;'
        f'margin-bottom:8px;background:white;'
        f'transition:transform 0.15s,box-shadow 0.15s;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="font-size:2rem;font-weight:700;color:{NAVY};">'
        f'{route["total_minutes"]}분{lf_badge}</span>'
        f'<span style="font-size:0.95rem;color:#666;">환승 {route["transfers"]}회</span>'
        f'</div>'
        f'<div style="font-size:1.1rem;color:#333;margin-bottom:4px;">{type_icon} {route["summary"]}</div>'
        f'<div style="font-size:1.1rem;color:#333;margin-bottom:12px;">'
        f'💰 {payment:,}원 · <b style="color:{NAVY};">🚶 도보 {total_walk}m</b></div>'
        f'<div style="background:rgba(0,47,108,0.06);border-radius:10px;padding:14px 18px;">'
        f'<span style="font-size:1.6rem;font-weight:700;color:{NAVY};">🚌 {route["low_floor_bus_no"]}</span>'
        f'{_arrival_html_inline(bus_arrival, NAVY)}'
        f'</div>'
        f'</div>',
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
