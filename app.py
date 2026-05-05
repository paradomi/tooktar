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
render_header("교통약자를 위한 교통안내 앱", show_settings=True)

if "favorite_places" not in st.session_state:
    st.session_state["favorite_places"] = FAVORITE_PLACES.copy()

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
fav_left, fav_right = st.columns([4, 1])
with fav_left:
    st.markdown("### ⭐ 자주 가는 곳")
with fav_right:
    st.write("")
    editing = st.session_state.get("edit_fav", False)
    if st.button("완료" if editing else "✏️ 편집", key="edit_fav_btn", use_container_width=True):
        st.session_state["edit_fav"] = not editing
        st.rerun()

if st.session_state.get("edit_fav", False):
    # ── 편집 모드 ──

    # 추가 폼
    with st.form("add_favorite_form", clear_on_submit=True):
        icon_options = ["🏠", "🏢", "🏥", "🏫", "🛒", "👨‍👩‍👧", "⛪", "🏛️", "🏋️", "🍽️", "☕", "📚"]
        col1, col2 = st.columns([1, 3])
        with col1:
            icon_input = st.selectbox("아이콘", icon_options, label_visibility="collapsed")
        with col2:
            label_input = st.text_input("장소명", placeholder="예: 회사, 병원")
        address_input = st.text_input("주소", placeholder="상세 주소를 입력하세요")
        submitted = st.form_submit_button("추가하기", use_container_width=True)
        if submitted:
            if not label_input or not address_input:
                st.error("장소명과 주소를 입력해주세요.")
            else:
                st.session_state["favorite_places"].append({
                    "icon": icon_input,
                    "label": label_input,
                    "address": address_input,
                })
                st.success(f"'{label_input}'이(가) 추가되었습니다!")
                st.rerun()

    st.write("")

    # 장소 목록 (순서 이동 + 삭제)
    favorites = st.session_state["favorite_places"]
    for idx, place in enumerate(favorites):
        c_icon, c_name, c_up, c_down, c_del = st.columns([1, 5, 1, 1, 1])
        with c_icon:
            st.markdown(f"### {place['icon']}")
        with c_name:
            st.markdown(f"**{place['label']}**")
            st.caption(place['address'])
        with c_up:
            if idx > 0:
                if st.button("⬆", key=f"up_{idx}", use_container_width=True):
                    favorites[idx], favorites[idx - 1] = favorites[idx - 1], favorites[idx]
                    st.rerun()
        with c_down:
            if idx < len(favorites) - 1:
                if st.button("⬇", key=f"down_{idx}", use_container_width=True):
                    favorites[idx], favorites[idx + 1] = favorites[idx + 1], favorites[idx]
                    st.rerun()
        with c_del:
            if st.button("🗑", key=f"del_{idx}", use_container_width=True):
                favorites.pop(idx)
                st.rerun()

else:
    # ── 일반 모드: 2열 버튼 그리드 ──
    cols = st.columns(2)
    for idx, place in enumerate(st.session_state["favorite_places"]):
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