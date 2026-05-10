"""툭 타 - 설정 화면"""

import streamlit as st
from components.styles import apply_global_styles
from components.header import render_header

NAVY = "#002F6C"

st.set_page_config(
    page_title="설정 - 툭 타",
    page_icon="⚙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_global_styles()
render_header("설정", back_target="app.py")

st.markdown(
    f'<div style="font-size:1.4rem;font-weight:700;color:{NAVY};margin:1rem 0 0.5rem 0;">🔤 글자 크기</div>',
    unsafe_allow_html=True,
)

font_options = ["작게", "보통", "크게", "매우 크게"]
current = st.session_state.get("font_size_level", "크게")

# 4개 컬럼으로 토글 버튼 그룹
_size_cols = st.columns(len(font_options))
for i, opt in enumerate(font_options):
    is_sel = current == opt
    with _size_cols[i]:
        if st.button(
            opt,
            key=f"size_{opt}",
            type="primary" if is_sel else "secondary",
            use_container_width=True,
        ):
            st.session_state["font_size_level"] = opt
            st.rerun()
