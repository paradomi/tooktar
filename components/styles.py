"""공통 스타일 - 고대비, 큰 터치 영역, 접근성 우선"""

import streamlit as st

def apply_global_styles():
    st.markdown("""
    <style>
        /* 모바일 앱 느낌의 좁은 레이아웃 */
        .main .block-container {
            max-width: 480px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* 모든 버튼 - 최소 56px 높이 (48dp 이상) */
        .stButton > button {
            min-height: 56px;
            font-size: 18px !important;
            font-weight: 600;
            border-radius: 12px;
            border: 2px solid #1f77b4;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            background-color: #1f77b4;
            color: white;
            transform: scale(1.01);
        }
        .stButton > button:active {
            transform: scale(0.98);
        }
        
        /* 입력창 큰 사이즈 */
        .stTextInput > div > div > input {
            font-size: 18px !important;
            min-height: 56px;
            padding: 12px 16px;
            border-radius: 12px;
            border: 2px solid #ccc;
        }
        .stTextInput > div > div > input:focus {
            border-color: #1f77b4;
        }
        
        /* 헤더 스타일 */
        h1 {
            font-size: 36px !important;
            text-align: center;
            margin-bottom: 8px;
        }
        h2 {
            font-size: 24px !important;
            margin-top: 24px;
        }
        h3 {
            font-size: 20px !important;
        }
        
        /* 카드 스타일 */
        .card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .card-highlight {
            border-color: #1f77b4;
            background: #f0f7ff;
        }
        
        /* 알림 박스 큰 폰트 */
        .stAlert {
            font-size: 18px !important;
            padding: 16px !important;
            border-radius: 12px !important;
        }
        
        /* 라디오/탭도 큼직하게 */
        .stRadio label {
            font-size: 18px !important;
            padding: 8px;
        }
    </style>
    """, unsafe_allow_html=True)