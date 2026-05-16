"""툭 타 - 홈/검색 화면 (네이비 테마)"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from streamlit_searchbox import st_searchbox
from streamlit_js_eval import get_geolocation

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

# ─── 로고 (텍스트, viewport 반응형) ───
st.markdown(
    f'<div style="text-align:center;margin:24px 0 16px 0;font-family:\'Gowun Batang\',serif;">'
    f'<div style="font-size:clamp(48px, 14vw, 96px);font-weight:700;color:{NAVY};letter-spacing:0.15em;line-height:1;">툭 타</div>'
    f'<div style="font-size:clamp(13px, 3.5vw, 20px);color:#555;margin-top:12px;letter-spacing:0.05em;">" 이동의 장벽을 툭, 넘다. "</div>'
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
    import streamlit.components.v1 as _components

    favorites = st.session_state["favorite_places"]

    # ── 새 장소 추가 폼 (편집 모드 상단) ──
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
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{NAVY};margin-bottom:8px;">'
        f'📋 저장된 장소</div>',
        unsafe_allow_html=True,
    )

    # ── Streamlit 네이티브 인라인 편집/삭제/순서변경 ──
    # 편집 모드(개별 항목): session_state["_editing_idx"]
    _editing_idx = st.session_state.get("_editing_idx", None)

    # 행별 컴팩트 스타일
    st.markdown(f"""
    <style>
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{
        flex-wrap: nowrap !important;
        gap: 4px !important;
        align-items: center !important;
    }}
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        min-width: 0 !important;
    }}
    div[data-testid="stButton"] button[kind="secondary"]:not(:has(strong)) {{
        min-height: 44px !important;
        height: 44px !important;
        padding: 0 !important;
        border-radius: 8px !important;
        border-width: 1px !important;
    }}
    .fav-row {{
        background: white;
        border: 1.5px solid {NAVY};
        border-radius: 10px;
        padding: 10px 14px;
        height: 44px;
        display: flex;
        align-items: center;
        gap: 10px;
        overflow: hidden;
        font-family: 'Gowun Batang','Noto Serif KR',serif;
    }}
    .fav-row .ico {{ font-size: 1.3rem; flex-shrink: 0; }}
    .fav-row .info {{ flex: 1; min-width: 0; overflow: hidden; }}
    .fav-row .lbl {{ font-weight: 700; color: {NAVY}; font-size: 0.95rem; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .fav-row .addr {{ font-size: 0.78rem; color: #777; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    </style>
    """, unsafe_allow_html=True)

    favs = favorites
    for idx, place in enumerate(favs):
        if _editing_idx == idx:
            # ── 인라인 편집 폼 ──
            with st.container(border=True):
                _e_cols = st.columns([1, 3])
                with _e_cols[0]:
                    _new_icon = st.selectbox(
                        "아이콘",
                        icon_options,
                        index=icon_options.index(place["icon"]) if place["icon"] in icon_options else 0,
                        key=f"edit_icon_{idx}",
                        label_visibility="collapsed",
                    )
                with _e_cols[1]:
                    _new_label = st.text_input(
                        "이름",
                        value=place["label"],
                        key=f"edit_label_{idx}",
                        label_visibility="collapsed",
                        placeholder="장소 이름",
                    )
                # 주소: 자동완성 searchbox
                _new_place = st_searchbox(
                    _place_search,
                    placeholder=f"🔍 주소 (현재: {place['address']})",
                    key=f"edit_addr_{idx}",
                )
                if _new_place:
                    _preview = (
                        _new_place.get("road_address_name")
                        or _new_place.get("address_name", "")
                    )
                    st.caption(f"📍 새 주소: **{_new_place.get('place_name','')}** — {_preview}")
                _btn_cols = st.columns([1, 1])
                with _btn_cols[0]:
                    if st.button("✅ 저장", key=f"save_{idx}", use_container_width=True, type="primary"):
                        if not _new_label:
                            st.error("이름을 입력해주세요.")
                        else:
                            favs[idx]["icon"] = _new_icon
                            favs[idx]["label"] = _new_label
                            if _new_place:
                                favs[idx]["address"] = _new_place.get("place_name", place["address"])
                                try:
                                    favs[idx]["lng"] = float(_new_place["x"])
                                    favs[idx]["lat"] = float(_new_place["y"])
                                except (KeyError, TypeError, ValueError):
                                    pass
                            st.session_state["favorite_places"] = favs
                            st.session_state.pop("_editing_idx", None)
                            st.rerun()
                with _btn_cols[1]:
                    if st.button("✕ 취소", key=f"cancel_{idx}", use_container_width=True):
                        st.session_state.pop("_editing_idx", None)
                        st.rerun()
        else:
            # ── 일반 행: 아이콘+이름+주소 | ⬆ | ⬇ | ✏️ | 🗑 ──
            _row_cols = st.columns([8, 1, 1, 1, 1])
            with _row_cols[0]:
                _lbl_safe = (place.get("label") or "").replace("<", "&lt;")
                _addr_safe = (place.get("address") or "").replace("<", "&lt;")
                _ico_safe = place.get("icon", "")
                st.markdown(
                    f'<div class="fav-row">'
                    f'<span class="ico">{_ico_safe}</span>'
                    f'<div class="info">'
                    f'<div class="lbl">{_lbl_safe}</div>'
                    f'<div class="addr">{_addr_safe}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with _row_cols[1]:
                if idx > 0 and st.button("⬆", key=f"up_{idx}", use_container_width=True):
                    favs[idx - 1], favs[idx] = favs[idx], favs[idx - 1]
                    st.session_state["favorite_places"] = favs
                    st.rerun()
                elif idx == 0:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
            with _row_cols[2]:
                if idx < len(favs) - 1 and st.button("⬇", key=f"down_{idx}", use_container_width=True):
                    favs[idx], favs[idx + 1] = favs[idx + 1], favs[idx]
                    st.session_state["favorite_places"] = favs
                    st.rerun()
                elif idx == len(favs) - 1:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
            with _row_cols[3]:
                if st.button("✏️", key=f"edit_{idx}", use_container_width=True):
                    st.session_state["_editing_idx"] = idx
                    st.rerun()
            with _row_cols[4]:
                if st.button("🗑", key=f"del_{idx}", use_container_width=True):
                    favs.pop(idx)
                    st.session_state["favorite_places"] = favs
                    st.session_state.pop("_editing_idx", None)
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
                # 출발지 우선순위:
                #   1) 실시간 GPS (gps_coord)
                #   2) place의 origin_* 필드
                #   3) DEFAULT_ORIGIN
                _gps_fix = st.session_state.get("gps_coord")
                if _gps_fix and _gps_fix.get("lat") is not None and _gps_fix.get("lng") is not None:
                    # GPS 좌표 → reverse geocode로 이름 만들기 (캐시 활용)
                    _gps_lat = float(_gps_fix["lat"])
                    _gps_lng = float(_gps_fix["lng"])
                    _gps_ck2 = f"gps_addr_{_gps_lat:.5f}_{_gps_lng:.5f}"
                    _gps_addr2 = st.session_state.get(_gps_ck2)
                    if not _gps_addr2:
                        _gps_addr2 = coord_to_address(_gps_lng, _gps_lat)
                        st.session_state[_gps_ck2] = _gps_addr2
                    if _gps_addr2:
                        st.session_state["origin_coord"] = _gps_addr2
                        st.session_state["origin_input"] = f"📍 {_gps_addr2['name']}"
                        st.session_state["_prev_origin"] = st.session_state["origin_input"]
                    else:
                        st.session_state["origin_coord"] = {
                            "name": "현재 위치",
                            "address": "",
                            "lng": _gps_lng, "lat": _gps_lat,
                        }
                        st.session_state["origin_input"] = "📍 현재 위치"
                        st.session_state["_prev_origin"] = "📍 현재 위치"
                elif "origin_lng" in place and "origin_lat" in place:
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
    /* st.columns 모바일에서도 가로 배치 유지 (collapse 차단), 비율은 streamlit 기본 유지 */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{
        flex-wrap: nowrap !important;
    }}
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        min-width: 0 !important;
    }}
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong) {{
        aspect-ratio: 1 / 1;
        height: auto;
        min-height: 140px;
        max-height: 220px;
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
        font-size: clamp(2.5rem, 12vw, 5rem);
        line-height: 1;
        margin: 0;
        white-space: pre-line;
    }}
    [data-testid="stMain"] [data-testid="stButton"] > button[kind="secondary"]:has(strong) strong {{
        font-size: clamp(1rem, 4vw, 1.6rem);
        font-weight: 700;
        color: {NAVY};
    }}
    </style>
    """, unsafe_allow_html=True)


# ─── 검색 영역 (자동완성) ───
st.markdown('<div class="search-section-title">📍 어디로 가시나요?</div>', unsafe_allow_html=True)


# ─── GPS 자동 감지 (페이지 로드 시 브라우저 위치 권한 자동 요청) ───
# 권한 거부/실패 시 조용히 fallback. 한 번 권한 허용하면 이후 방문은 무인 자동.
_gps_loc = get_geolocation()
if _gps_loc and isinstance(_gps_loc, dict):
    _coords = _gps_loc.get("coords") or {}
    _lat = _coords.get("latitude")
    _lng = _coords.get("longitude")
    if _lat is not None and _lng is not None:
        # 페이지 간 공유용: GPS 원시 좌표 저장 (모든 페이지에서 즉시 사용 가능)
        st.session_state["gps_coord"] = {"lat": float(_lat), "lng": float(_lng)}
        _gps_ck = f"gps_addr_{_lat:.5f}_{_lng:.5f}"
        if _gps_ck in st.session_state:
            _gps_addr = st.session_state[_gps_ck]
        else:
            _gps_addr = coord_to_address(_lng, _lat)
            st.session_state[_gps_ck] = _gps_addr
        if _gps_addr:
            st.session_state["origin_coord"] = _gps_addr
            st.session_state["origin_input"] = f"📍 {_gps_addr['name']}"
            st.session_state["_prev_origin"] = st.session_state["origin_input"]
            st.caption(f"📍 현재 위치: **{_gps_addr['name']}**")

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

# 모바일 rerun 시 searchbox 선택값 손실 대비: 즉시 session_state 백업
if selected_origin:
    st.session_state["_sb_origin_cache"] = selected_origin
if selected_dest:
    st.session_state["_sb_dest_cache"] = selected_dest


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
    # 모바일 rerun으로 searchbox 값 잃었을 때 캐시에서 복원
    final_origin = selected_origin or st.session_state.get("_sb_origin_cache")
    final_dest = selected_dest or st.session_state.get("_sb_dest_cache")
    if not final_dest:
        st.warning("도착지를 입력하고 자동완성에서 선택해주세요")
    else:
        # 출발지 우선순위: searchbox 선택(또는 캐시) > 이미 설정된 GPS/이전 값 > DEFAULT_ORIGIN
        if final_origin:
            _set_coord("origin_coord", "origin_input", final_origin)
            st.session_state["_prev_origin"] = st.session_state.get("origin_input", "")
        elif st.session_state.get("origin_coord") and st.session_state.get("origin_input", "").startswith("📍"):
            # GPS로 이미 설정됨 — 그대로 사용
            pass
        else:
            st.session_state["origin_input"] = "📍 현재 위치 (수원시 영통구)"
            st.session_state["origin_coord"] = DEFAULT_ORIGIN.copy()
            st.session_state["_prev_origin"] = "📍 현재 위치 (수원시 영통구)"
        # 도착지
        _set_coord("dest_coord", "selected_destination", final_dest)
        st.session_state["_prev_destination"] = st.session_state.get("selected_destination", "")
        # 캐시 소비 후 정리
        st.session_state.pop("_sb_origin_cache", None)
        st.session_state.pop("_sb_dest_cache", None)
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
