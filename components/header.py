"""앱 헤더"""

import streamlit as st

def render_header(subtitle=""):
    st.markdown("<h1>🚌 툭 타</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f"<p style='text-align: center; font-size: 16px; color: #666; margin-top: -8px;'>{subtitle}</p>",
            unsafe_allow_html=True
        )
    st.write("")