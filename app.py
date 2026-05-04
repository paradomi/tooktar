"""툭 타 - 홈/검색 화면"""

import streamlit as st
from components.styles import apply_global_styles
from components.header import render_header
from data.dummy_data import RECENT_SEARCHES, FAVORITE_PLACES

st.set_page_config(
    page_title="툭 타",
    page_icon="🚌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_global_styles()
render_header("지체장애인을 위한 배리어프리 교통 안내")

# ─── 출발지 / 도착지 검색 ───
st.markdown("### 어디로 가시나요?")

origin = st.text_input(
    "출발지",
    value="📍 현재 위치 (수원시 영통구)",
    key="origin_input",
    label_visibility="collapsed",
)

destination = st.text_input(
    "도착지",
    placeholder="🔍 도착지를 입력하세요",
    key="destination_input",
    label_visibility="collapsed",
)

if st.button("경로 찾기", use_container_width=True, type="primary"):
    if destination.strip():
        st.session_state["selected_destination"] = destination
        st.switch_page("pages/1_경로_탐색.py")
    else:
        st.warning("도착지를 입력해주세요")

st.write("---")

# ─── 자주 가는 곳 ───
st.markdown("### ⭐ 자주 가는 곳")

cols = st.columns(2)
for idx, place in enumerate(FAVORITE_PLACES):
    with cols[idx % 2]:
        if st.button(
            f"{place['icon']}\n\n**{place['label']}**",
            key=f"fav_{idx}",
            use_container_width=True,
        ):
            st.session_state["selected_destination"] = place["address"]
            st.switch_page("pages/1_경로_탐색.py")

st.write("")

# ─── 최근 검색 ───
st.markdown("### 🕐 최근 검색")

for idx, item in enumerate(RECENT_SEARCHES):
    if st.button(
        f"📍 {item['name']}  ·  {item['address']}",
        key=f"recent_{idx}",
        use_container_width=True,
    ):
        st.session_state["selected_destination"] = item["address"]
        st.switch_page("pages/1_경로_탐색.py")