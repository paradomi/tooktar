"""경로 탐색 결과 화면"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.styles import apply_global_styles
from components.header import render_header
from components.route_card import render_route_card
from data.dummy_data import ROUTE_RESULTS

st.set_page_config(page_title="경로 탐색", page_icon="🚌", layout="centered")

apply_global_styles()

# 뒤로가기
if st.button("← 뒤로", key="back_home"):
    st.switch_page("app.py")

render_header()

destination = st.session_state.get("selected_destination", "도착지")
st.markdown(f"### 🎯 {destination}")
st.caption(f"총 {len(ROUTE_RESULTS)}개 경로를 찾았습니다")

st.write("")

# 정렬 옵션
sort_option = st.radio(
    "정렬",
    ["휠체어 우선", "최단 시간", "최소 환승"],
    horizontal=True,
    label_visibility="collapsed",
)

st.write("")

# 정렬 적용
if sort_option == "휠체어 우선":
    routes = sorted(ROUTE_RESULTS, key=lambda r: -r["barrier_free_score"])
elif sort_option == "최단 시간":
    routes = sorted(ROUTE_RESULTS, key=lambda r: r["total_minutes"])
else:
    routes = sorted(ROUTE_RESULTS, key=lambda r: r["transfers"])

# 경로 카드 렌더링
for route in routes:
    render_route_card(route, key_prefix=sort_option)