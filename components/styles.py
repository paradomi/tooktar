"""공통 스타일 - 고대비, 큰 터치 영역, 접근성 우선"""

import streamlit as st

# 폰트 크기 프리셋 (작게 / 보통 / 크게 / 매우 크게)
FONT_SIZE_PRESETS = {
    "작게": {"body": 16, "button": 16, "h1": 32, "h2": 22, "h3": 18, "input": 16, "alert": 16},
    "보통": {"body": 18, "button": 18, "h1": 36, "h2": 24, "h3": 20, "input": 18, "alert": 18},
    "크게": {"body": 22, "button": 22, "h1": 42, "h2": 30, "h3": 26, "input": 22, "alert": 22},
    "매우 크게": {"body": 26, "button": 26, "h1": 48, "h2": 36, "h3": 32, "input": 26, "alert": 26},
}


_BASE_FONT_PX = {"작게": 14, "보통": 16, "크게": 19, "매우 크게": 22}


def apply_global_styles():
    level = st.session_state.get("font_size_level", "크게")
    f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["크게"])
    base_px = _BASE_FONT_PX.get(level, 16)

    st.markdown(f"""
    <style>
        /* 폰트: Gowun Batang (한글 명조) */
        @import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap');

        /* 베이스 폰트 크기 — 모든 rem 단위가 이 값을 참조하여 자동 스케일 */
        html {{ font-size: {base_px}px !important; }}

        /* 본문/입력은 Gowun Batang. span/div는 제외해서 Material Icons span을 망가뜨리지 않음.
           div는 body 상속으로 자동 적용됨. */
        html, body, [class*="css"], [data-testid="stApp"], [data-testid="stAppViewContainer"],
        .stMarkdown, .stText, .stButton button, .stFormSubmitButton button,
        input, textarea, select, label,
        h1, h2, h3, h4, h5, h6, p, a {{
            font-family: 'Gowun Batang', 'Noto Serif KR', serif !important;
        }}

        /* Expander 화살표 — testid 정확 매칭만으로 ▼/▲ 텍스트 대체 */
        [data-testid="stExpanderToggleIcon"],
        [data-testid="stExpanderHeaderToggleIcon"] {{
            font-size: 0 !important;
            color: transparent !important;
            width: 18px !important;
            height: 18px !important;
            position: relative !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        [data-testid="stExpanderToggleIcon"]::before,
        [data-testid="stExpanderHeaderToggleIcon"]::before {{
            content: "▼" !important;
            font-size: 12px !important;
            color: #444 !important;
            font-family: 'Gowun Batang', sans-serif !important;
            display: inline-block !important;
        }}
        [data-testid="stExpander"] details[open] [data-testid="stExpanderToggleIcon"]::before,
        [data-testid="stExpander"] details[open] [data-testid="stExpanderHeaderToggleIcon"]::before {{
            content: "▲" !important;
        }}

        /* 기본 사이드바 및 토글 버튼 완전히 숨기기 */
        [data-testid="collapsedControl"] {{ display: none !important; }}
        [data-testid="stSidebarNav"] {{ display: none !important; }}
        [data-testid="stSidebarCollapseControl"] {{ display: none !important; }}
        [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
        button[kind="header"] {{ display: none !important; }}
        [data-testid="stSidebar"] {{ display: none !important; }}
        
        /* 모바일 포트레이트 레이아웃 (1080×1920 기준) */
        .main .block-container {{
            max-width: 1080px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }}
        
        /* 모든 버튼 - 최소 56px 높이 (48dp 이상) */
        .stButton > button {{
            min-height: 56px;
            font-size: {f['button']}px !important;
            font-weight: 600;
            border-radius: 12px;
            border: 2px solid #1f77b4;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            background-color: #1f77b4;
            color: white;
            transform: scale(1.01);
        }}
        .stButton > button:active {{
            transform: scale(0.98);
        }}
        
        /* 입력창 큰 사이즈 */
        .stTextInput > div > div > input {{
            font-size: {f['input']}px !important;
            min-height: 56px;
            padding: 12px 16px;
            border-radius: 12px;
            border: 2px solid #ccc;
        }}
        .stTextInput > div > div > input:focus {{
            border-color: #1f77b4;
        }}
        
        /* 헤더 스타일 */
        h1 {{
            font-size: {f['h1']}px !important;
            text-align: center;
            margin-bottom: 8px;
        }}
        h2 {{
            font-size: {f['h2']}px !important;
            margin-top: 24px;
        }}
        h3 {{
            font-size: {f['h3']}px !important;
        }}
        
        /* 본문 텍스트 */
        .stMarkdown p, .stMarkdown li {{
            font-size: {f['body']}px !important;
        }}
        
        /* 카드 스타일 */
        .card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .card-highlight {{
            border-color: #1f77b4;
            background: #f0f7ff;
        }}
        
        /* 알림 박스 큰 폰트 */
        .stAlert {{
            font-size: {f['alert']}px !important;
            padding: 16px !important;
            border-radius: 12px !important;
        }}
        
        /* 라디오/탭도 큼직하게 */
        .stRadio label {{
            font-size: {f['body']}px !important;
            padding: 8px;
        }}
        
        /* Expander 헤더 */
        .streamlit-expanderHeader, 
        details summary,
        [data-testid="stExpander"] summary span {{
            font-size: {f['body']}px !important;
            font-weight: 600 !important;
        }}
        
        /* Expander 내부 콘텐츠 */
        [data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {{
            font-size: {f['body']}px !important;
        }}
        
        /* Toggle(토글) 라벨 */
        .stToggle label span {{
            font-size: {f['body']}px !important;
        }}
        
        /* Caption */
        .stCaption, [data-testid="stCaptionContainer"] {{
            font-size: {max(f['body'] - 4, 12)}px !important;
        }}
        
        /* Selectbox */
        .stSelectbox label, .stSelectbox div[data-baseweb="select"] span {{
            font-size: {f['body']}px !important;
        }}
        
        /* Form 제출 버튼 */
        .stFormSubmitButton > button {{
            font-size: {f['button']}px !important;
        }}
    </style>
    """, unsafe_allow_html=True)