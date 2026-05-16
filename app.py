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

# ─── 자주가는곳 URL 쿼리 파라미터 처리 (SortableJS iframe → top frame 액션) ───
_qp = st.query_params
if "fav_act" in _qp:
    _act = _qp["fav_act"]
    _favs_qp = st.session_state.get("favorite_places", [])
    if _act == "reorder":
        try:
            _new_idx = [int(x) for x in _qp["order"].split(",")]
            if sorted(_new_idx) == list(range(len(_favs_qp))):
                st.session_state["favorite_places"] = [_favs_qp[i] for i in _new_idx]
        except (ValueError, KeyError):
            pass
    elif _act == "delete":
        try:
            _i = int(_qp["idx"])
            if 0 <= _i < len(_favs_qp):
                _favs_qp.pop(_i)
                st.session_state["favorite_places"] = _favs_qp
        except (ValueError, KeyError):
            pass
    elif _act == "edit":
        try:
            _i = int(_qp["idx"])
            _new_label = _qp.get("label", "")
            _new_icon = _qp.get("icon", "")
            _new_address = _qp.get("address", "")
            if 0 <= _i < len(_favs_qp):
                if _new_label:
                    _favs_qp[_i]["label"] = _new_label
                if _new_icon:
                    _favs_qp[_i]["icon"] = _new_icon
                if _new_address and _new_address != _favs_qp[_i].get("address", ""):
                    # 카카오 geocode로 좌표 재조회
                    from services.geocode import address_to_coord as _addr_to_coord
                    _geo = _addr_to_coord(_new_address)
                    if _geo:
                        _favs_qp[_i]["address"] = _new_address
                        _favs_qp[_i]["lng"] = _geo["lng"]
                        _favs_qp[_i]["lat"] = _geo["lat"]
                    else:
                        # 실패 메시지 저장 (다음 페이지에서 표시)
                        st.session_state["_fav_edit_error"] = (
                            f"⚠️ '{_new_address}' 주소를 찾을 수 없어 좌표 업데이트에 실패했습니다. "
                            f"다른 주소로 다시 시도해주세요."
                        )
                st.session_state["favorite_places"] = _favs_qp
        except (ValueError, KeyError):
            pass
    # 쿼리 파라미터 정리 (무한 루프 방지)
    st.query_params.clear()
    # 액션 처리 후 편집 모드 유지
    st.session_state["edit_fav"] = True
    st.rerun()

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

# 자주가는곳 편집 에러 메시지 (주소 geocoding 실패 등)
if "_fav_edit_error" in st.session_state:
    st.error(st.session_state.pop("_fav_edit_error"))

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

    # ── SortableJS 기반 드래그 + 인라인 편집/삭제 ──
    _FAV_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
<style>
body { margin: 0; padding: 4px; font-family: 'Gowun Batang', 'Noto Serif KR', serif; background: white; }
#list { list-style: none; padding: 0; margin: 0; }
.row {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px; margin-bottom: 8px;
  background: white; border: 2px solid #002F6C; border-radius: 12px;
  min-height: 56px; box-sizing: border-box;
}
.row.dragging { opacity: 0.6; transform: scale(0.98); }
.icon { font-size: 1.6rem; flex-shrink: 0; }
.info { flex: 1; min-width: 0; overflow: hidden; }
.info .lbl { font-weight: 700; color: #002F6C; font-size: 1.05rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.info .addr { font-size: 0.85rem; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.actions { display: flex; gap: 6px; flex-shrink: 0; align-items: center; }
.actions button {
  width: 36px; height: 36px; border: none; background: rgba(0,47,108,0.08);
  border-radius: 8px; cursor: pointer; font-size: 1rem; padding: 0;
}
.actions button:hover { background: rgba(0,47,108,0.18); }
.handle { cursor: grab; color: #888; user-select: none; font-size: 1.4rem; padding: 0 4px; line-height: 1; }
.handle:active { cursor: grabbing; }
.row.editing { background: #FFF8E1; border-color: #FFA726; }
.edit-form { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; align-items: center; }
.edit-form input { padding: 6px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.95rem; font-family: inherit; }
.edit-form .icon-input { width: 50px; text-align: center; }
.edit-form .label-input { flex: 0 0 100px; min-width: 80px; }
.edit-form .address-input { flex: 1 1 100%; min-width: 0; }
.save-btn, .cancel-btn { padding: 6px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.95rem; font-family: inherit; white-space: nowrap; }
.save-btn { background: #002F6C; color: white; }
.cancel-btn { background: #ccc; color: #333; }
</style>
</head>
<body>
<ul id="list">
__ROWS__
</ul>
<script>
const list = document.getElementById('list');
Sortable.create(list, {
  handle: '.handle',
  animation: 150,
  chosenClass: 'dragging',
  onEnd: function() {
    const order = Array.from(list.children).map(function(li) { return li.dataset.origIdx; });
    navigateTo({fav_act: 'reorder', order: order.join(',')});
  }
});

function deleteItem(idx) {
  if (!confirm('삭제할까요?')) return;
  navigateTo({fav_act: 'delete', idx: String(idx)});
}

function startEdit(idx) {
  document.querySelectorAll('.row').forEach(function(r) { r.classList.remove('editing'); });
  document.querySelectorAll('.edit-form').forEach(function(f) { f.remove(); });
  document.querySelectorAll('.normal-view').forEach(function(v) { v.style.display = ''; });
  const row = document.querySelector('li[data-orig-idx="' + idx + '"]');
  if (!row) return;
  row.classList.add('editing');
  const nv = row.querySelector('.normal-view');
  if (nv) nv.style.display = 'none';
  const currentLabel = row.dataset.label;
  const currentIcon = row.dataset.icon;
  const currentAddress = row.dataset.address || '';
  const form = document.createElement('div');
  form.className = 'edit-form';
  form.innerHTML = '<input class="icon-input" maxlength="3" value="' + currentIcon + '" title="아이콘">'
    + '<input class="label-input" value="' + currentLabel + '" placeholder="이름">'
    + '<button class="save-btn">저장</button>'
    + '<button class="cancel-btn">취소</button>'
    + '<input class="address-input" value="' + currentAddress.replace(/"/g, '&quot;') + '" placeholder="주소 (예: 수원시청, 아주대학교병원)">';
  const actionsEl = row.querySelector('.actions');
  row.insertBefore(form, actionsEl);
  form.querySelector('.save-btn').addEventListener('click', function() {
    const newLabel = form.querySelector('.label-input').value.trim();
    const newIcon = form.querySelector('.icon-input').value.trim();
    const newAddress = form.querySelector('.address-input').value.trim();
    if (!newLabel) { alert('이름을 입력해주세요.'); return; }
    if (!newAddress) { alert('주소를 입력해주세요.'); return; }
    navigateTo({fav_act: 'edit', idx: String(idx), label: newLabel, icon: newIcon, address: newAddress});
  });
  form.querySelector('.cancel-btn').addEventListener('click', function() {
    row.classList.remove('editing');
    if (nv) nv.style.display = '';
    form.remove();
  });
}

function navigateTo(params) {
  try {
    const url = new URL(window.top.location.href);
    Object.keys(params).forEach(function(k) { url.searchParams.set(k, params[k]); });
    const a = document.createElement('a');
    a.target = '_top';
    a.href = url.toString();
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
  } catch(e) {
    const f = document.createElement('form');
    f.method = 'GET';
    f.target = '_top';
    f.action = window.location.pathname;
    Object.keys(params).forEach(function(k) {
      const inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = k; inp.value = params[k];
      f.appendChild(inp);
    });
    document.body.appendChild(f);
    f.submit();
  }
}
</script>
</body>
</html>"""

    _rows_html = []
    for _i, _p in enumerate(favorites):
        _lbl = (_p.get("label") or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        _addr = (_p.get("address") or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        _ico = (_p.get("icon") or "").replace('"', "&quot;")
        _rows_html.append(
            f'<li class="row" data-orig-idx="{_i}" data-label="{_lbl}" data-icon="{_ico}" data-address="{_addr}">'
            f'<div class="normal-view" style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">'
            f'<span class="icon">{_ico}</span>'
            f'<div class="info"><div class="lbl">{_lbl}</div><div class="addr">{_addr}</div></div>'
            f'</div>'
            f'<div class="actions">'
            f'<button onclick="startEdit({_i})" title="편집">✏️</button>'
            f'<button onclick="deleteItem({_i})" title="삭제">🗑</button>'
            f'<span class="handle" title="드래그하여 순서 변경">&#8801;</span>'
            f'</div>'
            f'</li>'
        )

    _full_html = _FAV_HTML_TEMPLATE.replace("__ROWS__", "\n".join(_rows_html))
    _h = max(200, 60 + 80 * len(favorites))
    _components.html(_full_html, height=_h, scrolling=False)

    st.caption("✏️ 편집은 이름과 아이콘만 가능합니다. 주소 변경은 삭제 후 재추가하세요.")

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
