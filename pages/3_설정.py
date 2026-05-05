"""툭 타 - 설정 화면"""

import streamlit as st
from components.styles import apply_global_styles
from components.header import render_header

st.set_page_config(
    page_title="설정 - 툭 타",
    page_icon="⚙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_global_styles()
render_header("설정", show_home=True)

# ─── 폰트 크기 설정 ───
st.markdown("### 🔤 글자 크기")

font_options = ["작게", "보통", "크게", "매우 크게"]
current = st.session_state.get("font_size_level", "보통")
current_idx = font_options.index(current) if current in font_options else 1

selected = st.radio(
    "글자 크기 선택",
    font_options,
    index=current_idx,
    horizontal=True,
    label_visibility="collapsed",
)

if selected != current:
    st.session_state["font_size_level"] = selected
    st.rerun()

st.write("---")

# ─── 저상버스 표시 설정 ───
st.markdown("### ♿ 저상버스 표시")

if "show_low_floor" not in st.session_state:
    st.session_state["show_low_floor"] = True

low_floor_on = st.toggle(
    "경로 안내에서 저상버스 도착 정보 표시",
    value=st.session_state["show_low_floor"],
    key="low_floor_toggle",
)

if low_floor_on != st.session_state["show_low_floor"]:
    st.session_state["show_low_floor"] = low_floor_on
    st.rerun()
