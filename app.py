"""툭 타 - 홈/검색 화면 (네이비 테마)"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from streamlit_searchbox import st_searchbox
from streamlit_geolocation import streamlit_geolocation

from components.styles import apply_global_styles
from data.dummy_data import FAVORITE_PLACES
from services.kakao_local import search_places as _kakao_search_places
from services.geocode import coord_to_address
from utils.recent import load_recent, add_recent, remove_recent

NAVY = "#002F6C"
GOWUN_FONT = "'Gowun Batang', 'Noto Serif KR', serif"

# 출발지 미선택 시 기본 좌표 (수원시청 — 시연/저상버스 검증된 위치)
DEFAULT_ORIGIN = {
    "name": "현재 위치 (수원시 영통구)",
    "address": "경기 수원시 팔달구 효원로 241",
    "lng": 127.028715898311,
    "lat": 37.263584678785,
}

st.set_page_config(
    page_title="툭 타",
    page_icon="🚌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_global_styles()

# Streamlit 기본 헤더 숨김 + 네이비 테마 일관 디자인
st.markdown(f"""
<style>
[data-testid="stHeader"] {{ display: none; }}
[data-testid="stSidebarNav"] {{ display: none; }}
.block-container {{ padding-top: 0.5rem; padding-bottom: 2rem; }}

/* 검색 input focus 시 네이비 강조 */
.stTextInput > div > div > input:focus {{
    border-color: {NAVY} !important;
    box-shadow: 0 0 0 1px {NAVY} !important;
}}
/* primary 버튼 네이비 */
.stButton > button[kind="primary"] {{
    background-color: {NAVY} !important;
    border-color: {NAVY} !important;
    color: white !important;
    font-weight: 700 !important;
    height: 56px !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
}}
.stButton > button[kind="primary"]:hover {{
    background-color: #001F4C !important;
    border-color: #001F4C !important;
}}

/* secondary 버튼 중 자주가는곳 카드(strong 포함)가 아닌 경우만 NAVY 테두리 */
[data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:not(:has(strong)) {{
    border: 2px solid {NAVY} !important;
    color: {NAVY} !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    background: white !important;
}}
[data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:not(:has(strong)):hover {{
    background: rgba(0, 47, 108, 0.06) !important;
    border-color: {NAVY} !important;
    color: {NAVY} !important;
}}

/* 검색 영역 헤더 색 */
.search-section-title {{
    color: {NAVY};
    font-weight: 700;
    font-size: 1.3rem;
    margin: 1.5rem 0 0.5rem 0;
}}

/* TextInput 기본 라운드 */
.stTextInput > div > div > input {{
    border-radius: 12px !important;
    height: 50px !important;
    font-size: 1rem !important;
}}
</style>
""", unsafe_allow_html=True)

# 즐겨찾기 초기화
if "favorite_places" not in st.session_state:
    st.session_state["favorite_places"] = FAVORITE_PLACES.copy()

# ─── 페이지 전환 플래그 처리 ───
if st.session_state.get("_pending_nav"):
    target = st.session_state.pop("_pending_nav")
    st.switch_page(target)


# ─── 공통 함수 ───
def _place_search(query: str):
    """카카오 로컬 키워드 검색 → 자동완성 옵션 [(label, value_dict), ...]."""
    if not query or not query.strip():
        return []
    docs = _kakao_search_places(query.strip(), size=8)
    out = []
    for d in docs:
        place = d.get("place_name", "")
        addr = d.get("road_address_name") or d.get("address_name") or ""
        label = f"{place} · {addr}" if addr else place
        out.append((label, d))
    return out


# ─── 콜백 정의 ───
def go_settings():
    st.session_state["_pending_nav"] = "pages/3_설정.py"


def go_route_with_address(address: str):
    def _handler():
        st.session_state["selected_destination"] = address
        st.session_state["_pending_nav"] = "pages/1_경로_탐색.py"
    return _handler


def toggle_edit():
    st.session_state["edit_fav"] = not st.session_state.get("edit_fav", False)


# ─── 상단: 설정 아이콘 (streamlit 버튼) ───
_settings_cols = st.columns([1, 5])
with _settings_cols[0]:
    if st.button("⚙️ 설정", key="home_to_settings", use_container_width=True):
        st.switch_page("pages/3_설정.py")

# ─── 로고 (텍스트, 글자 크기 설정 무관 고정) ───
st.markdown(
    f'<div style="text-align:center;margin:32px 0 24px 0;font-family:\'Gowun Batang\',serif;">'
    f'<div style="font-size:96px;font-weight:700;color:{NAVY};letter-spacing:0.2em;line-height:1;">툭   타</div>'
    f'<div style="font-size:20px;color:#555;margin-top:20px;letter-spacing:0.05em;">" 이동의 장벽을 툭, 넘다. "</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── 자주 가는 곳 헤더 + 편집 토글 (streamlit) ───
_fav_left, _fav_right = st.columns([4, 1])
with _fav_left:
    st.markdown(
        f'<div style="font-size:1.5rem;font-weight:700;color:{NAVY};margin-top:1rem;">⭐ 자주 가는 곳</div>',
        unsafe_allow_html=True,
    )
with _fav_right:
    editing = st.session_state.get("edit_fav", False)
    if st.button("완료" if editing else "✏️ 편집", key="fav_edit_toggle", use_container_width=True):
        st.session_state["edit_fav"] = not editing
        st.rerun()


# ─── 자주 가는 곳 본체 ───
if st.session_state.get("edit_fav", False):
    # ── 편집 모드: 자동완성 검색 + 추가 ──
    icon_options = ["🏠", "🏢", "🏥", "🏫", "🛒", "👨‍👩‍👧", "⛪", "🏛️", "🏋️", "🍽️", "☕", "📚"]
    col1, col2 = st.columns([1, 3])
    with col1:
        icon_input = st.selectbox(
            "아이콘", icon_options, key="fav_icon_input", label_visibility="collapsed"
        )
    with col2:
        label_input = st.text_input(
            "장소명", placeholder="예: 회사, 병원", key="fav_label_input"
        )
    # 주소 검색 (자동완성)
    fav_selected_place = st_searchbox(
        _place_search,
        placeholder="🔍 주소 또는 장소 검색",
        key="fav_address_searchbox",
    )
    if fav_selected_place:
        addr_preview = (
            fav_selected_place.get("road_address_name")
            or fav_selected_place.get("address_name", "")
        )
        st.caption(f"📍 선택됨: **{fav_selected_place.get('place_name','')}** — {addr_preview}")

    if st.button("➕ 추가하기", key="fav_add_btn", use_container_width=True, type="primary"):
        if not label_input:
            st.error("장소명을 입력해주세요.")
        elif not fav_selected_place:
            st.error("주소를 검색해서 선택해주세요.")
        else:
            new_place = {
                "icon": icon_input,
                "label": label_input,
                "address": fav_selected_place.get("place_name", ""),
                "lng": float(fav_selected_place["x"]),
                "lat": float(fav_selected_place["y"]),
            }
            st.session_state["favorite_places"].append(new_place)
            st.success(f"'{label_input}'이(가) 추가되었습니다!")
            st.rerun()

    st.write("")

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
    # ── 일반 모드: streamlit 버튼 그리드 (정사각형, NAVY 테두리) ──
    favs = st.session_state["favorite_places"]
    cols = st.columns(2)
    for idx, place in enumerate(favs):
        with cols[idx % 2]:
            if st.button(
                f"{place['icon']}\n\n**{place['label']}**",
                key=f"fav_{idx}",
                use_container_width=True,
            ):
                # 자주가는곳 좌표로 도착지 고정
                addr = place["address"]
                st.session_state["selected_destination"] = addr
                if "lng" in place and "lat" in place:
                    st.session_state["dest_coord"] = {
                        "name": place.get("label", addr),
                        "address": addr,
                        "lng": float(place["lng"]),
                        "lat": float(place["lat"]),
                    }
                else:
                    st.session_state.pop("dest_coord", None)
                st.session_state["_prev_destination"] = addr
                # 출발지: origin_* 필드가 있으면 그걸로, 없으면 DEFAULT_ORIGIN
                if "origin_lng" in place and "origin_lat" in place:
                    origin_name = place.get("origin_name", "출발지")
                    origin_addr = place.get("origin_address", "")
                    st.session_state["origin_input"] = f"📍 {origin_name}"
                    st.session_state["origin_coord"] = {
                        "name": origin_name,
                        "address": origin_addr,
                        "lng": float(place["origin_lng"]),
                        "lat": float(place["origin_lat"]),
                    }
                    st.session_state["_prev_origin"] = f"📍 {origin_name}"
                else:
                    st.session_state["origin_input"] = "📍 현재 위치 (수원시 영통구)"
                    st.session_state["origin_coord"] = DEFAULT_ORIGIN.copy()
                    st.session_state["_prev_origin"] = "📍 현재 위치 (수원시 영통구)"
                # ODsay 검색 결과/loadLane/도보 폴리라인 캐시도 정리
                for k in list(st.session_state.keys()):
                    if k.startswith("odsay_") or k.startswith("lane_") \
                       or k.startswith("tmap_walk_") or k.startswith("route_lf_score_"):
                        st.session_state.pop(k, None)
                st.switch_page("pages/1_경로_탐색.py")
    # MUI 카드 시각 효과는 CSS 인젝션으로 보강
    st.markdown(f"""
    <style>
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong) {{
        aspect-ratio: 1 / 1;
        height: auto;
        min-height: 180px;
        border: 2px solid {NAVY} !important;
        border-radius: 20px !important;
        background: white !important;
        color: {NAVY} !important;
        transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
        gap: 0;
        padding: 0.4rem;
    }}
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong):hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0, 47, 108, 0.25);
        background: rgba(0, 47, 108, 0.04) !important;
        border-color: {NAVY} !important;
    }}
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong) p {{
        font-size: 5rem;
        line-height: 1;
        margin: 0;
        white-space: pre-line;
    }}
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong) strong {{
        font-size: 1.6rem;
        font-weight: 700;
        color: {NAVY};
    }}
    </style>
    """, unsafe_allow_html=True)


# ─── 검색 영역 (자동완성) ───
st.markdown('<div class="search-section-title">📍 어디로 가시나요?</div>', unsafe_allow_html=True)


gps_col1, gps_col2 = st.columns([1, 3])
with gps_col1:
    loc = streamlit_geolocation()
with gps_col2:
    st.caption("📍 위 버튼을 눌러 GPS로 현재 위치를 설정할 수 있습니다")

if loc and loc.get("latitude") and loc.get("longitude"):
    lat = loc["latitude"]
    lng = loc["longitude"]
    gps_ck = f"gps_addr_{lat}_{lng}"
    if gps_ck in st.session_state:
        gps_addr = st.session_state[gps_ck]
    else:
        gps_addr = coord_to_address(lng, lat)
        st.session_state[gps_ck] = gps_addr
    if gps_addr:
        st.session_state["origin_coord"] = gps_addr
        st.session_state["origin_input"] = f"📍 {gps_addr['name']}"
        st.session_state["_prev_origin"] = st.session_state["origin_input"]
        st.success(f"📍 현재 위치: **{gps_addr['name']}** ({gps_addr['address']})")

selected_origin = st_searchbox(
    _place_search,
    placeholder="📍 출발지 (비워두면 현재 위치 사용)",
    key="origin_searchbox",
)

selected_dest = st_searchbox(
    _place_search,
    placeholder="🔍 도착지를 입력하세요 (예: 아주대학교병원)",
    key="destination_searchbox",
)


def _set_coord(state_key, name_key, place_dict):
    """선택된 카카오 place dict → session_state에 좌표 + 텍스트 저장."""
    try:
        st.session_state[state_key] = {
            "name": place_dict.get("place_name", ""),
            "address": place_dict.get("road_address_name") or place_dict.get("address_name", ""),
            "lng": float(place_dict["x"]),
            "lat": float(place_dict["y"]),
        }
        st.session_state[name_key] = place_dict.get("place_name", "")
        return True
    except (KeyError, TypeError, ValueError):
        return False


if st.button("경로 찾기", use_container_width=True, type="primary"):
    if not selected_dest:
        st.warning("도착지를 입력하고 자동완성에서 선택해주세요")
    else:
        # 출발지 우선순위: searchbox 선택 > 이미 설정된 GPS/이전 값 > DEFAULT_ORIGIN
        if selected_origin:
            _set_coord("origin_coord", "origin_input", selected_origin)
            st.session_state["_prev_origin"] = st.session_state.get("origin_input", "")
        elif st.session_state.get("origin_coord") and st.session_state.get("origin_input", "").startswith("📍"):
            # GPS로 이미 설정됨 — 그대로 사용
            pass
        else:
            st.session_state["origin_input"] = "📍 현재 위치 (수원시 영통구)"
            st.session_state["origin_coord"] = DEFAULT_ORIGIN.copy()
            st.session_state["_prev_origin"] = "📍 현재 위치 (수원시 영통구)"
        # 도착지
        _set_coord("dest_coord", "selected_destination", selected_dest)
        st.session_state["_prev_destination"] = st.session_state.get("selected_destination", "")
        add_recent(
            origin_coord=st.session_state.get("origin_coord"),
            dest_coord=st.session_state.get("dest_coord"),
            origin_name=st.session_state.get("origin_input", "").replace("📍 ", ""),
            dest_name=st.session_state.get("selected_destination", ""),
        )
        st.switch_page("pages/1_경로_탐색.py")

# ─── 최근 검색 섹션 ───
recents = load_recent()
if recents:
    st.markdown(
        f'<div style="font-size:1.2rem;font-weight:700;color:{NAVY};margin:1.5rem 0 0.5rem 0;">'
        f'🕒 최근 검색</div>',
        unsafe_allow_html=True,
    )
    for idx, item in enumerate(recents):
        o = item.get("origin", {})
        d = item.get("dest", {})
        c_main, c_del = st.columns([10, 1])
        with c_main:
            label = f"{o.get('name', '?')}  →  {d.get('name', '?')}"
            if st.button(label, key=f"recent_{idx}", use_container_width=True):
                # 좌표 복원
                st.session_state["origin_coord"] = {
                    "name": o.get("name", ""),
                    "address": o.get("address", ""),
                    "lng": o.get("lng"), "lat": o.get("lat"),
                }
                st.session_state["origin_input"] = f"📍 {o.get('name', '')}"
                st.session_state["_prev_origin"] = st.session_state["origin_input"]
                st.session_state["dest_coord"] = {
                    "name": d.get("name", ""),
                    "address": d.get("address", ""),
                    "lng": d.get("lng"), "lat": d.get("lat"),
                }
                st.session_state["selected_destination"] = d.get("name", "")
                st.session_state["_prev_destination"] = d.get("name", "")
                # ODsay 등 캐시 정리
                for k in list(st.session_state.keys()):
                    if k.startswith("odsay_") or k.startswith("lane_") \
                       or k.startswith("tmap_walk_") or k.startswith("route_lf_score_"):
                        st.session_state.pop(k, None)
                st.switch_page("pages/1_경로_탐색.py")
        with c_del:
            if st.button("✕", key=f"recent_del_{idx}", use_container_width=True):
                remove_recent(idx)
                st.rerun()
