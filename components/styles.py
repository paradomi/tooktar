"""공통 스타일 - 고대비, 큰 터치 영역, 접근성 우선"""

import streamlit as st

# 폰트 크기 프리셋 (작게 / 보통 / 크게 / 매우 크게)
FONT_SIZE_PRESETS = {
    "작게": {"body": 16, "button": 16, "h1": 32, "h2": 22, "h3": 18, "input": 16, "alert": 16},
    "보통": {"body": 18, "button": 18, "h1": 36, "h2": 24, "h3": 20, "input": 18, "alert": 18},
    "크게": {"body": 22, "button": 22, "h1": 42, "h2": 30, "h3": 26, "input": 22, "alert": 22},
    "매우 크게": {"body": 26, "button": 26, "h1": 48, "h2": 36, "h3": 32, "input": 26, "alert": 26},
}


def apply_global_styles():
    level = st.session_state.get("font_size_level", "보통")
    f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])

    st.markdown(f"""
    <style>
        /* 기본 사이드바 및 토글 버튼 완전히 숨기기 */
        [data-testid="collapsedControl"] {{ display: none !important; }}
        [data-testid="stSidebarNav"] {{ display: none !important; }}
        
        /* 모바일 앱 느낌의 좁은 레이아웃 */
        .main .block-container {{
            max-width: 480px;
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