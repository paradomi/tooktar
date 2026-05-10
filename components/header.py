"""앱 헤더 (HTML 로고 + Streamlit 버튼)"""
import streamlit as st

NAVY = "#002F6C"


def render_header(subtitle="", back_target=None, show_home=False, show_settings=False, show_logo=False):
    """페이지 헤더 — 메인 외 페이지는 로고 미표시, 뒤로/설정 버튼만.

    Args:
        subtitle: 부제 (show_logo=True일 때만 표시)
        back_target: 뒤로 가기 경로
        show_home: (deprecated) back_target="app.py" 매핑
        show_settings: ⚙️ 설정 버튼 표시
        show_logo: 가운데 "툭 타" 로고 표시 (메인 화면에서만 True)
    """
    if show_home and not back_target:
        back_target = "app.py"

    if show_logo:
        cols = st.columns([1.4, 4, 1])
        with cols[0]:
            if back_target:
                if st.button("← 뒤로", key="hdr_back_btn", use_container_width=True, help="이전 페이지"):
                    st.switch_page(back_target)
            elif show_settings:
                if st.button("⚙️", key="hdr_settings_btn", use_container_width=True, help="설정"):
                    st.switch_page("pages/3_설정.py")
            else:
                st.write("")
        with cols[1]:
            sub_html = (
                f'<div style="font-size:15px;color:#666;margin-top:6px;">{subtitle}</div>'
                if subtitle else ""
            )
            st.markdown(
                f'<div style="text-align:center;min-height:56px;">'
                f'<div style="font-size:35px;font-weight:700;color:{NAVY};letter-spacing:0.15em;line-height:1;">툭 타</div>'
                f'{sub_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with cols[2]:
            st.write("")
    else:
        # 로고 없이 좌측 액션 버튼만
        if back_target:
            if st.button("← 뒤로", key="hdr_back_btn", help="이전 페이지"):
                st.switch_page(back_target)
        elif show_settings:
            if st.button("⚙️ 설정", key="hdr_settings_btn", help="설정"):
                st.switch_page("pages/3_설정.py")
