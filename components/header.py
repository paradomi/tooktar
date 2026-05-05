"""앱 헤더"""

import streamlit as st
from components.styles import FONT_SIZE_PRESETS


def render_header(subtitle="", show_home=False, show_settings=False):
    level = st.session_state.get("font_size_level", "보통")
    f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])
    fs_sub = max(f["body"] - 2, 13)

    # 상단 네비게이션 및 헤더 영역
    cols = st.columns([1, 4, 1])

    with cols[0]:
        st.write("")
        if show_home:
            if st.button("🏠 홈", use_container_width=True, key="header_home"):
                st.switch_page("app.py")
        elif show_settings:
            if st.button("⚙️ 설정", use_container_width=True, key="header_settings"):
                st.switch_page("pages/3_설정.py")

    with cols[1]:
        st.markdown("<h1>🚌 툭 타</h1>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(
                f'<p style="text-align:center;font-size:{fs_sub}px;color:#666;margin-top:-4px;">{subtitle}</p>',
                unsafe_allow_html=True,
            )

    with cols[2]:
        st.write("")

    st.write("")