"""경로 상세 화면 - ODsay mapObj 기반 실제 경로 + 카카오맵 + 교통약자 정보"""

import json
import streamlit as st
import streamlit.components.v1 as components
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from components.styles import apply_global_styles, FONT_SIZE_PRESETS
from components.header import render_header

NAVY = "#002F6C"
from services.odsay_api import load_lane
from services.tmap_api import pedestrian_route
from services.bus_arrival import get_arrivals as _get_bus_arrivals
from data.dummy_data import AI_BRIEFING

st.set_page_config(page_title="경로 상세", page_icon="🗺️", layout="centered")

apply_global_styles()

st.markdown("""
<style>
/* 상세 페이지는 컨텐츠가 많아 메인보다 넓게 */
.main .block-container { max-width: 760px !important; }

[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"] p {
    font-size: 1.6rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

level = st.session_state.get("font_size_level", "크게")
f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["크게"])
fs_body = f["body"]
fs_small = max(fs_body - 4, 12)
fs_badge = max(fs_body - 6, 11)
fs_title = f["h3"]

import pandas as _pd

_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "station_codes.csv")
try:
    _stn_df = _pd.read_csv(_csv_path)
except Exception:
    _stn_df = None


def _stin_cd_of(line_cd, station_name):
    """노선코드 + 역명으로 STIN_CD 반환. 부분매칭 허용."""
    if _stn_df is None or _stn_df.empty:
        return None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    exact = sub[sub["STIN_NM"] == nm]
    if not exact.empty:
        return exact.iloc[0]["STIN_CD"]
    partial = sub[sub["STIN_NM"].str.startswith(nm, na=False)]
    if not partial.empty:
        return partial.iloc[0]["STIN_CD"]
    return None


def _stin_num(stin_cd):
    """STIN_CD에서 숫자만 추출해 int 반환 (비교용). 실패 시 None."""
    if not stin_cd:
        return None
    import re as _re
    m = _re.search(r"(\d+)", str(stin_cd))
    return int(m.group(1)) if m else None


def _line_terminals(line_cd):
    """노선의 양 끝 종점 역명 반환 (작은 STIN_CD 쪽, 큰 쪽)."""
    if _stn_df is None or _stn_df.empty:
        return None, None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    if sub.empty:
        return None, None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None, None
    pairs.sort(key=lambda p: p[0])
    return pairs[0][1], pairs[-1][1]  # (min_terminal, max_terminal)


def _line_cd_of_station(station_name):
    """역명으로 LN_CD 자동 추론 (첫 매칭). 환승역은 첫 노선만."""
    if _stn_df is None or _stn_df.empty:
        return None
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    rows = _stn_df[_stn_df["STIN_NM"] == nm]
    if rows.empty:
        rows = _stn_df[_stn_df["STIN_NM"].str.startswith(nm, na=False)]
    if rows.empty:
        return None
    return str(rows.iloc[0]["LN_CD"])


def _adjacent_station(line_cd, start_num, direction):
    """노선 내 start_num의 한 칸 옆 역명 반환 (direction: -1 또는 +1)."""
    if _stn_df is None or _stn_df.empty:
        return None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    if sub.empty:
        return None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None
    pairs.sort(key=lambda p: p[0])
    nums = [p[0] for p in pairs]
    if start_num not in nums:
        return None
    idx = nums.index(start_num)
    nxt = idx + direction
    if 0 <= nxt < len(pairs):
        return pairs[nxt][1]
    return None


def _direction_label(start_name, end_name):
    """ODsay subway step의 (start_name, end_name)으로 (종점, 인접역) 방면 라벨 생성.
    실패 시 '{end_name} 방면' fallback."""
    fallback = f"{end_name} 방면"
    if not start_name or not end_name:
        return fallback
    ln_cd = _line_cd_of_station(start_name)
    if not ln_cd:
        return fallback
    start_num = _stin_num(_stin_cd_of(ln_cd, start_name))
    end_num = _stin_num(_stin_cd_of(ln_cd, end_name))
    if start_num is None or end_num is None or start_num == end_num:
        return fallback
    direction = -1 if end_num < start_num else +1
    t_low, t_high = _line_terminals(ln_cd)
    terminal = t_low if direction == -1 else t_high
    adj = _adjacent_station(ln_cd, start_num, direction)
    if terminal and adj and terminal != adj:
        return f"({terminal}, {adj}) 방면"
    if terminal:
        return f"{terminal} 방면"
    return fallback


def _render_station_panel(name, info, target_end_name=None):
    """KRIC 데이터로 자체 교통약자 패널 렌더링 (출구/방면 선택형)"""
    import re
    NAVY_C = "#002F6C"
    full_nm = info.get("full_name", name)

    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:700;color:{NAVY_C};margin-bottom:8px;">'
        f'🚇 {full_nm}</div>',
        unsafe_allow_html=True,
    )

    movement = info.get("movement", [])
    if movement:
        # 이동 경로 그룹별로 정리 (mvPathMgNo로 구분)
        groups = {}
        for item in movement:
            mg = item.get("mvPathMgNo", 0)
            groups.setdefault(mg, []).append(item)

        # 출구별로 묶기 (stMovePath에서 "N번" 추출)
        exit_groups = {}  # {"3번 출입구": [(mg_no, items, ed_path), ...]}
        for mg_no, items in groups.items():
            items_sorted = sorted(items, key=lambda x: x.get("exitMvTpOrdr", 0))
            first = items_sorted[0]
            st_path = first.get("stMovePath", "")
            ed_path = first.get("edMovePath", "")

            # 출구 번호 추출 (예: "3번 출입구", "3번,4번 출입구 중간 엘리베이터")
            exit_nums = re.findall(r"(\d+)번", st_path)
            if exit_nums:
                if len(exit_nums) == 1:
                    exit_label = f"{exit_nums[0]}번 출입구"
                else:
                    exit_label = f"{','.join(exit_nums)}번 출입구"
            else:
                exit_label = st_path[:30] if st_path else f"경로 {mg_no}"

            exit_groups.setdefault(exit_label, []).append((mg_no, items_sorted, ed_path))

        # 출구 선택 UI
        exit_options = list(exit_groups.keys())
        exit_options.sort(key=lambda s: int(re.search(r"\d+", s).group()) if re.search(r"\d+", s) else 999)

        selected_exit = st.selectbox(
            "이용할 출입구 선택",
            exit_options,
            key=f"exit_sel_{name}",
        )

        # 해당 출구의 방면 옵션 (여러 방면 있으면)
        paths_for_exit = exit_groups[selected_exit]
        if len(paths_for_exit) > 1:
            # ── 방면 라벨 보강 + 자동 default 결정 ──
            ln_cd = info["codes"][1]
            start_stin_num = _stin_num(_stin_cd_of(ln_cd, name))
            target_stin_num = (
                _stin_num(_stin_cd_of(ln_cd, target_end_name))
                if target_end_name
                else None
            )

            target_dir = None  # +1 (증가), -1 (감소)
            if start_stin_num is not None and target_stin_num is not None:
                if target_stin_num < start_stin_num:
                    target_dir = -1
                elif target_stin_num > start_stin_num:
                    target_dir = +1

            terminal_low, terminal_high = _line_terminals(ln_cd)

            labeled_options = []
            default_idx = 0
            for i, (mg, items, ed_path) in enumerate(paths_for_exit):
                # ed_path 예: "매탄권선 방면" → head_word="매탄권선"
                head_word = ed_path.split(" ")[0] if ed_path else ""
                # 접미사 "행"이 붙은 경우 제거 (예: "왕십리행")
                head_clean = head_word.rstrip("행").strip()
                head_stin_num = _stin_num(_stin_cd_of(ln_cd, head_clean))

                opt_dir = None
                if start_stin_num is not None and head_stin_num is not None:
                    if head_stin_num < start_stin_num:
                        opt_dir = -1
                    elif head_stin_num > start_stin_num:
                        opt_dir = +1

                # 종점 결정
                if opt_dir == -1:
                    terminal = terminal_low
                elif opt_dir == +1:
                    terminal = terminal_high
                else:
                    terminal = None

                # 라벨 형식: "(종점, 인접역) 방면"
                if terminal and head_clean and terminal != head_clean:
                    base_label = f"({terminal}, {head_clean}) 방면"
                elif terminal:
                    base_label = f"{terminal} 방면"
                else:
                    base_label = ed_path

                # ✓ / 반대방향 표시
                if target_dir is not None and opt_dir == target_dir and target_end_name:
                    label = f"✓ {base_label}"
                    default_idx = i
                elif target_dir is not None and opt_dir is not None and opt_dir == -target_dir:
                    label = f"{base_label} (반대 방향)"
                else:
                    label = base_label
                labeled_options.append(label)

            selected_label = st.selectbox(
                "방면 선택",
                labeled_options,
                index=default_idx,
                key=f"ed_sel_{name}_{selected_exit}",
            )
            selected_idx = labeled_options.index(selected_label)
            chosen = paths_for_exit[selected_idx]
        else:
            chosen = paths_for_exit[0]

        mg_no, items_sorted, ed_path = chosen
        first = items_sorted[0]
        st_path = first.get("stMovePath", "")

        # 선택된 경로 렌더링
        st.markdown(
            f'<div style="margin-top:14px;padding:10px 14px;'
            f'background:rgba(0,47,108,0.06);border-left:4px solid {NAVY_C};'
            f'border-radius:8px;">'
            f'<div style="font-weight:700;color:{NAVY_C};font-size:1rem;">'
            f'🛣️ {st_path} → {ed_path}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        img = first.get("imgPath", "")
        if img:
            img_https = img.replace("http://", "https://", 1)
            zoom_html = f'''
<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=yes" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#fff; }}
  #wrap {{ position:relative; width:100%; height:360px; overflow:hidden;
          border-radius:12px; border:1px solid #ddd; touch-action:none; }}
  #content {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; }}
  #content img {{ width:100%; max-width:600px; display:block; -webkit-user-drag:none; user-select:none; }}
  .hint {{ position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.55);
          color:white; font-size:11px; padding:4px 8px; border-radius:6px;
          pointer-events:none; font-family:sans-serif; z-index:2; }}
  .open-link {{ position:absolute; bottom:8px; right:8px; background:rgba(0,47,108,0.85);
                color:white; font-size:11px; padding:4px 9px; border-radius:6px;
                text-decoration:none; font-family:sans-serif; z-index:2; }}
  .open-link:hover {{ background:rgba(0,47,108,1); }}
</style>
</head><body>
<div id="wrap">
  <div id="content"><img src="{img_https}" alt="역내 도면" /></div>
  <div class="hint">🖱️ 휠 / 👆 핀치로 확대</div>
  <a class="open-link" href="{img_https}" target="_blank" rel="noopener">🔍 원본</a>
</div>
<script src="https://unpkg.com/panzoom@9.4.3/dist/panzoom.min.js"></script>
<script>
  window.addEventListener('load', function() {{
    var elem = document.getElementById('content');
    if (window.panzoom) {{
      panzoom(elem, {{
        minZoom: 1, maxZoom: 6,
        bounds: true, boundsPadding: 0.1,
        smoothScroll: false
      }});
    }}
  }});
</script>
</body></html>
'''
            components.html(zoom_html, height=380)
        for item in items_sorted:
            desc = item.get("mvContDtl", "")
            if desc:
                st.markdown(
                    f'<div style="padding:8px 14px;background:white;'
                    f'border:1px solid #e0e0e0;border-radius:8px;margin-top:6px;'
                    f'font-size:0.95rem;color:#333;">{desc}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("이 역의 이동 경로 정보가 없습니다.")

    transfer = info.get("transfer", [])
    if transfer:
        with st.expander(f"🔄 환승 이동 정보 ({len(transfer)}건)"):
            for item in transfer:
                desc = item.get("mvContDtl") or item.get("dtLoc") or ""
                if desc:
                    st.markdown(f"- {desc}")

    lift = info.get("lift", [])
    if lift:
        with st.expander(f"♿ 휠체어 리프트 위치 ({len(lift)}건)"):
            for item in lift:
                exit_no = item.get("exitNo")
                loc = item.get("dtLoc") or item.get("liftLctnDtl") or item.get("mvContDtl") or ""
                # 층 정보: B1, 지하1층 → 지상1층 등
                fr = item.get("grndDvNmFr", "")
                fr_floor = item.get("runStinFlorFr", "")
                to = item.get("grndDvNmTo", "")
                to_floor = item.get("runStinFlorTo", "")
                floor_info = ""
                if fr and to and (fr_floor or to_floor):
                    floor_info = f" · {fr}{fr_floor}층 → {to}{to_floor}층"
                if exit_no:
                    label = f"**{exit_no}번 출입구**: {loc}{floor_info}"
                else:
                    label = f"{loc}{floor_info}" if loc else "위치 정보 없음"
                st.markdown(f"- {label}")


render_header(back_target="pages/1_경로_탐색.py")

# 페이지 전환 플래그 처리
if st.session_state.get("_pending_nav"):
    target = st.session_state.pop("_pending_nav")
    st.switch_page(target)

KAKAO_JS_KEY = os.getenv("KAKAO_JS_KEY") or os.getenv("KAKAO_SDK_DOMAIN", "")

# ─── 선택된 경로 가져오기 ───
route_id = st.session_state.get("selected_route_id", 1)
odsay_routes = st.session_state.get("odsay_routes", [])
selected = next((r for r in odsay_routes if r["id"] == route_id), None)

if not selected:
    st.warning("경로 정보가 없습니다. 경로 탐색 페이지로 돌아가주세요.")
    st.stop()

steps = selected.get("steps", [])
map_obj = selected.get("map_obj", "")

_route_mode = st.session_state.get("route_mode", "fast")
_search_option = 4 if _route_mode == "wheel" else 0
_walk_color = "#7B1FA2" if _route_mode == "wheel" else "#FF8C00"

# ─── 1. ODsay loadLane으로 폴리라인 데이터 획득 ───
if _route_mode == "wheel":
    st.markdown(
        f'<div style="'
        f'background:rgba(0,47,108,0.08);'
        f'border-left:4px solid {NAVY};'
        f'border-radius:12px;'
        f'padding:14px 18px;'
        f'margin-bottom:16px;">'
        f'<div style="color:{NAVY};font-weight:700;font-size:1.05rem;margin-bottom:4px;">'
        f'♿ 휠체어 맞춤 경로</div>'
        f'<div style="color:#444;font-size:0.92rem;">'
        f'계단을 제외한 도보 경로로 안내합니다 (지도의 보라색 점선)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
st.markdown("### 🗺️ 경로 지도")

lane_data = None
if map_obj:
    cache_key = f"lane_{map_obj}"
    if cache_key in st.session_state:
        lane_data = st.session_state[cache_key]
    else:
        with st.spinner("🗺️ 실제 주행 경로를 불러오는 중..."):
            lane_data = load_lane(map_obj)
        if lane_data:
            st.session_state[cache_key] = lane_data

# ─── 2. 카카오맵에 폴리라인 렌더링 ───
lane_sections = []
if lane_data and "lane" in lane_data:
    for lane in lane_data["lane"]:
        lane_class = lane.get("class", 0)
        sections = lane.get("section", [])
        for section in sections:
            graph_pos = section.get("graphPos", [])
            coords = []
            if isinstance(graph_pos, list):
                for pt in graph_pos:
                    try:
                        coords.append({"lat": float(pt["y"]), "lng": float(pt["x"])})
                    except (KeyError, ValueError, TypeError):
                        pass
            elif isinstance(graph_pos, str) and graph_pos:
                for pt in graph_pos.split(" "):
                    parts = pt.split(",")
                    if len(parts) == 2:
                        try:
                            coords.append({"lat": float(parts[1]), "lng": float(parts[0])})
                        except ValueError:
                            pass
            if coords:
                if lane_class == 1:
                    color = "#2DB400"
                elif lane_class == 2:
                    color = "#1f77b4"
                else:
                    color = "#999999"
                lane_sections.append({"coords": coords, "color": color})

# 도보 구간 (Tmap 보행자 경로 API → 실패 시 직선 fallback)
origin_coord = st.session_state.get("origin_coord", {})
dest_coord = st.session_state.get("dest_coord", {})

walk_lines = []
for idx, step in enumerate(steps):
    if step["type"] != "walk":
        continue
    sx, sy = step.get("start_x"), step.get("start_y")
    ex, ey = step.get("end_x"), step.get("end_y")
    # 인접 step에서 좌표 보충
    if not (sx and sy):
        for j in range(idx - 1, -1, -1):
            ps = steps[j]
            if ps.get("end_x") and ps.get("end_y"):
                sx, sy = ps["end_x"], ps["end_y"]
                break
        if not (sx and sy) and origin_coord:
            sx, sy = origin_coord.get("lng"), origin_coord.get("lat")
    if not (ex and ey):
        for j in range(idx + 1, len(steps)):
            ns = steps[j]
            if ns.get("start_x") and ns.get("start_y"):
                ex, ey = ns["start_x"], ns["start_y"]
                break
        if not (ex and ey) and dest_coord:
            ex, ey = dest_coord.get("lng"), dest_coord.get("lat")
    if not (sx and sy and ex and ey):
        continue
    cache_key = f"tmap_walk_{sx}_{sy}_{ex}_{ey}_opt{_search_option}"
    tmap_coords = st.session_state.get(cache_key)
    if not tmap_coords:
        tmap_coords = pedestrian_route(
            sx, sy, ex, ey,
            start_name=step.get("start_name", "출발"),
            end_name=step.get("end_name", "도착"),
            search_option=_search_option,
        )
        if tmap_coords:
            st.session_state[cache_key] = tmap_coords
    if tmap_coords:
        coords = tmap_coords
    else:
        coords = [
            {"lat": float(sy), "lng": float(sx)},
            {"lat": float(ey), "lng": float(ex)},
        ]
    walk_lines.append({"coords": coords, "color": _walk_color})

all_coords = []
for sec in lane_sections:
    all_coords.extend(sec["coords"])
for wl in walk_lines:
    all_coords.extend(wl["coords"])
if origin_coord:
    all_coords.append({"lat": origin_coord.get("lat", 0), "lng": origin_coord.get("lng", 0)})
if dest_coord:
    all_coords.append({"lat": dest_coord.get("lat", 0), "lng": dest_coord.get("lng", 0)})

if not all_coords:
    all_coords = [{"lat": 37.27, "lng": 127.03}]

center_lat = sum(c["lat"] for c in all_coords) / len(all_coords)
center_lng = sum(c["lng"] for c in all_coords) / len(all_coords)

sections_json = json.dumps(lane_sections, ensure_ascii=False)
walk_json = json.dumps(walk_lines, ensure_ascii=False)

origin_name = origin_coord.get("name", "출발") if origin_coord else "출발"
dest_name = dest_coord.get("name", "도착") if dest_coord else "도착"
origin_lat = origin_coord.get("lat", center_lat)
origin_lng = origin_coord.get("lng", center_lng)
dest_lat = dest_coord.get("lat", center_lat)
dest_lng = dest_coord.get("lng", center_lng)

kakao_map_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&autoload=false"></script>
<style>
  * {{ margin: 0; padding: 0; }}
  #map {{ width: 100%; height: 450px; border-radius: 16px; }}
</style>
</head><body>
<div id="map"></div>
<script>
kakao.maps.load(function() {{
  var container = document.getElementById('map');
  var map = new kakao.maps.Map(container, {{
    center: new kakao.maps.LatLng({center_lat}, {center_lng}),
    level: 5,
    mapTypeId: kakao.maps.MapTypeId.HYBRID
  }});

  // 일반/위성 토글 컨트롤 (우측 상단)
  var mapTypeControl = new kakao.maps.MapTypeControl();
  map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
  // 줌 컨트롤
  var zoomControl = new kakao.maps.ZoomControl();
  map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

  var bounds = new kakao.maps.LatLngBounds();

  // 위성 배경 가시성 ↑ : 흰색 외곽 + 컬러 안쪽 두 겹 폴리라인
  var sections = {sections_json};
  sections.forEach(function(sec) {{
    var path = sec.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    // 외곽선 (흰색, 두꺼움)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 11, strokeColor: '#FFFFFF',
      strokeOpacity: 0.95, strokeStyle: 'solid'
    }});
    // 안쪽 (컬러)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 7, strokeColor: sec.color,
      strokeOpacity: 1.0, strokeStyle: 'solid'
    }});
  }});

  var walks = {walk_json};
  walks.forEach(function(w) {{
    var path = w.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    // 외곽선 (흰색, 점선)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 8, strokeColor: '#FFFFFF',
      strokeOpacity: 0.9, strokeStyle: 'shortdashdot'
    }});
    // 안쪽 (컬러)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 5, strokeColor: w.color,
      strokeOpacity: 1.0, strokeStyle: 'shortdashdot'
    }});
  }});

  var startPos = new kakao.maps.LatLng({origin_lat}, {origin_lng});
  bounds.extend(startPos);
  new kakao.maps.InfoWindow({{
    content: '<div style="padding:4px 8px;font-size:12px;font-weight:bold;color:#1565c0;">\\ud83d\\udea9 {origin_name}</div>'
  }}).open(map, new kakao.maps.Marker({{ map: map, position: startPos }}));

  var endPos = new kakao.maps.LatLng({dest_lat}, {dest_lng});
  bounds.extend(endPos);
  new kakao.maps.InfoWindow({{
    content: '<div style="padding:4px 8px;font-size:12px;font-weight:bold;color:#c62828;">\\ud83d\\udccd {dest_name}</div>'
  }}).open(map, new kakao.maps.Marker({{ map: map, position: endPos }}));

  map.setBounds(bounds, 80);
}});
</script>
</body></html>"""

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(static_dir, exist_ok=True)
map_file = os.path.join(static_dir, "map.html")
with open(map_file, "w", encoding="utf-8") as f:
    f.write(kakao_map_html)

components.iframe("app/static/map.html", height=470, scrolling=False)

_walk_legend = (
    '<span>🟪 <b>도보 (계단 제외)</b></span>'
    if _route_mode == "wheel"
    else '<span>🟧 <b>도보</b></span>'
)
st.markdown(f"""
<div style="display:flex;gap:16px;justify-content:center;font-size:13px;margin-top:-8px;margin-bottom:12px;">
    <span>🟦 <b>지하철</b></span>
    <span>🟩 <b>버스</b></span>
    {_walk_legend}
</div>
""", unsafe_allow_html=True)

# ─── 3. 경로 요약 ───
st.markdown(f"### 📋 {selected['total_minutes']}분 · {selected['summary']}")
st.caption(f"💰 요금 {selected.get('payment', 0):,}원 · 🚶 도보 {selected.get('total_walk', 0)}m")

# ─── 4. 경로 단계별 정보 ───
for step in steps:
    icon = {"walk": "🚶", "bus": "🚌", "transfer": "🔄", "subway": "🚇"}.get(step["type"], "•")
    bf_mark = "✅" if step.get("barrier_free") else "⚠️"
    stype = step["type"]

    if stype == "bus":
        border_color = "#1f77b4"
    elif stype == "subway":
        border_color = "#2DB400"
    elif stype == "walk":
        border_color = "#FF8C00"
    else:
        border_color = "#999"

    if stype in ("bus", "subway"):
        # 방면 강조 카드
        if stype == "subway":
            line = step.get("line_name", "")
            head = f"{icon} {line}"
        else:  # bus
            bus_no = step.get("bus_no", "")
            head = f"{icon} {bus_no}번 버스"
            # ODsay bus_type은 저상 정보 아님 — GBIS 실시간 lowPlate로만 판단

        start_nm = step.get("start_name", "")
        end_nm = step.get("end_name", "")
        station_count = step.get("station_count", 0)
        section_time = step.get("section_time", 0)
        meta_unit = "역" if stype == "subway" else "정거장"

        # 지하철: (종점, 인접역) 방면 자동 추론, 버스는 단순 도착역 방면
        if stype == "subway":
            direction_label = _direction_label(start_nm, end_nm)
        else:
            direction_label = f"{end_nm} 방면"

        # 버스 실시간 도착정보 (GBIS 우선)
        arrival_html = ""
        if stype == "bus":
            bus_no = step.get("bus_no", "")
            sx, sy = step.get("start_x"), step.get("start_y")
            station_id = step.get("start_id")
            ods_city = step.get("city_code")
            cache_k = f"bus_arr_{station_id}_{bus_no}_{sx}_{sy}"
            if cache_k in st.session_state:
                arrivals = st.session_state[cache_k]
            else:
                arrivals = _get_bus_arrivals(
                    station_id=station_id, lng=sx, lat=sy, city_code_hint=ods_city,
                )
                st.session_state[cache_k] = arrivals
            matched = [a for a in (arrivals or []) if a.get("route_name") == bus_no]
            if matched:
                preds = matched[0].get("predictions", [])[:2]
                if preds:
                    badges = []
                    has_low_floor = False
                    for p in preds:
                        m = p.get("minutes")
                        is_low = p.get("low_floor")
                        low_tag = f' <span style="background:{NAVY};color:white;font-size:0.7rem;font-weight:700;padding:1px 6px;border-radius:8px;">♿저상</span>' if is_low else ""
                        if is_low:
                            has_low_floor = True
                        stops = f" ({p['stops_left']}정류장 전)" if p.get("stops_left") else ""
                        badges.append(f"<b>{m}분 후</b>{low_tag}{stops}")
                    # 저상 차량 도착 예정이면 카드 머리에도 라벨 추가
                    if has_low_floor:
                        head += (
                            f' <span style="display:inline-block;background:{NAVY};color:white;'
                            f'font-size:0.75rem;font-weight:700;padding:2px 8px;border-radius:10px;'
                            f'margin-left:6px;vertical-align:middle;">♿ 저상 도착</span>'
                        )
                    arrival_html = (
                        f'<div style="background:rgba(0,47,108,0.08);border-radius:8px;'
                        f'padding:8px 12px;margin:6px 0;font-size:0.95rem;color:{NAVY};">'
                        f'⏱️ {" · ".join(badges)}</div>'
                    )

        st.markdown(
            f'<div style="padding:14px 18px;background:#f8f9fa;'
            f'border-left:5px solid {border_color};margin-bottom:6px;'
            f'border-radius:10px;font-size:{fs_body}px;color:#333;">'
            f'<div style="font-weight:700;margin-bottom:4px;">{head} {bf_mark}</div>'
            f'<div style="font-size:{fs_body + 2}px;color:{NAVY};font-weight:700;'
            f'margin:6px 0;">↗ {direction_label}</div>'
            f'{arrival_html}'
            f'<div style="font-size:{max(fs_body - 2, 13)}px;color:#666;">'
            f'{start_nm} 승차 · {station_count}{meta_unit} · {section_time}분</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # walk / transfer 등 기존 형식
        st.markdown(
            f'<div style="padding:12px 16px;background:#f8f9fa;'
            f'border-left:5px solid {border_color};margin-bottom:4px;'
            f'border-radius:8px;font-size:{fs_body}px;color:#333;">'
            f'{icon} {step["desc"]}  {bf_mark}'
            f'</div>',
            unsafe_allow_html=True,
        )

st.write("---")

# ─── 5. 교통약자 시설 정보 (카카오맵 지하철역 임베드) ───
st.markdown("### ♿ 교통약자 시설 정보")

subway_steps = [s for s in steps if s["type"] == "subway"]
station_names = []
_seen = set()
for s in subway_steps:
    for nm in (s.get("start_name", ""), s.get("end_name", "")):
        if nm and nm not in _seen:
            station_names.append(nm)
            _seen.add(nm)

if station_names:
    # KRIC 역코드 매핑 (캐시)
    from services.rail_portal import (
        find_station_codes, get_station_movement,
        get_elevator_movement, get_transfer_movement, get_wheelchair_lift,
    )

    station_data = {}  # {역명: {codes, movement, elevator, transfer, lift, full_name}}
    for nm in station_names:
        cache_key = f"kric_{nm}"
        if cache_key in st.session_state:
            station_data[nm] = st.session_state[cache_key]
            continue
        codes = find_station_codes(nm)
        if not codes:
            continue
        rail_op, ln, stin, full_nm = codes
        info = {
            "codes": (rail_op, ln, stin),
            "full_name": full_nm,
            "movement": get_station_movement(rail_op, ln, stin),
            "elevator": get_elevator_movement(rail_op, ln, stin),
            "transfer": get_transfer_movement(rail_op, ln, stin),
            "lift": get_wheelchair_lift(rail_op, ln, stin),
        }
        station_data[nm] = info
        st.session_state[cache_key] = info

    if station_data:
        names = list(station_data.keys())
        tabs = st.tabs([f"🚇 {n}" for n in names])
        for tab, nm in zip(tabs, names):
            # subway step 중 시작역이 nm인 것 찾기 → target_end_name 전달
            target_end = None
            for s in subway_steps:
                s_start = s.get("start_name", "")
                if s_start == nm or s_start.startswith(nm) or nm.startswith(s_start):
                    target_end = s.get("end_name", "")
                    break
            with tab:
                info = station_data[nm]
                _render_station_panel(nm, info, target_end_name=target_end)
    else:
        st.info("이 경로의 지하철역 교통약자 정보를 불러올 수 없습니다.")
else:
    st.info("이 경로에는 지하철 구간이 없습니다.")

st.write("---")

# ─── 6. AI 요약 브리핑 ───
st.markdown("### 🤖 AI 경로 브리핑")
st.markdown(
    f'<div style="background:linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);border-left:4px solid #ff9800;border-radius:12px;padding:18px;font-size:{fs_body}px;line-height:1.6;color:#333;">'
    f'{AI_BRIEFING.replace(chr(10), "<br><br>")}'
    f'</div>',
    unsafe_allow_html=True,
)

st.write("")

# ─── 액션 버튼 ───
_act1, _act2 = st.columns(2)
with _act1:
    if st.button("🔊 음성 안내", key="action_voice", use_container_width=True):
        st.toast("음성 안내를 시작합니다")
with _act2:
    if st.button("📤 보호자 공유", key="action_share", use_container_width=True, type="primary"):
        st.toast("보호자에게 경로를 공유했습니다")