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
from services.odsay_api import load_lane
from data.dummy_data import ACCESSIBILITY_INFO, AI_BRIEFING

st.set_page_config(page_title="경로 상세", page_icon="🗺️", layout="centered")

apply_global_styles()

level = st.session_state.get("font_size_level", "보통")
f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])
fs_body = f["body"]
fs_small = max(fs_body - 4, 12)
fs_badge = max(fs_body - 6, 11)
fs_title = f["h3"]

if st.button("← 경로 목록", key="back_routes"):
    st.switch_page("pages/1_경로_탐색.py")

render_header()

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

# ─── 1. ODsay loadLane으로 폴리라인 데이터 획득 ───
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

# 도보 구간 (subPath의 start/end 좌표로 직선 표시)
walk_lines = []
for step in steps:
    if step["type"] == "walk":
        sx, sy = step.get("start_x"), step.get("start_y")
        ex, ey = step.get("end_x"), step.get("end_y")
        if sx and sy and ex and ey:
            walk_lines.append({
                "coords": [
                    {"lat": float(sy), "lng": float(sx)},
                    {"lat": float(ey), "lng": float(ex)},
                ],
                "color": "#FF8C00",
            })

origin_coord = st.session_state.get("origin_coord", {})
dest_coord = st.session_state.get("dest_coord", {})

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
    level: 5
  }});

  var bounds = new kakao.maps.LatLngBounds();

  var sections = {sections_json};
  sections.forEach(function(sec) {{
    var path = sec.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 6, strokeColor: sec.color,
      strokeOpacity: 0.85, strokeStyle: 'solid'
    }});
  }});

  var walks = {walk_json};
  walks.forEach(function(w) {{
    var path = w.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 4, strokeColor: w.color,
      strokeOpacity: 0.7, strokeStyle: 'shortdashdot'
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

st.markdown(
    '<iframe src="/app/static/map.html" width="100%" height="470" '
    'style="border:none;border-radius:16px;" loading="lazy"></iframe>',
    unsafe_allow_html=True,
)

st.markdown("""
<div style="display:flex;gap:16px;justify-content:center;font-size:13px;margin-top:-8px;margin-bottom:12px;">
    <span>🟦 <b>버스</b></span>
    <span>🟩 <b>지하철</b></span>
    <span>🟧 <b>도보</b></span>
</div>
""", unsafe_allow_html=True)

# ─── 3. 경로 요약 ───
st.markdown(f"### 📋 {selected['total_minutes']}분 · {selected['summary']}")
st.caption(f"💰 요금 {selected.get('payment', 0):,}원 · 🚶 도보 {selected.get('total_walk', 0)}m")

# ─── 4. 경로 단계별 정보 ───
for step in steps:
    icon = {"walk": "🚶", "bus": "🚌", "transfer": "🔄", "subway": "🚇"}.get(step["type"], "•")
    bf_mark = "✅" if step.get("barrier_free") else "⚠️"

    if step["type"] == "bus":
        border_color = "#1f77b4"
    elif step["type"] == "subway":
        border_color = "#2DB400"
    elif step["type"] == "walk":
        border_color = "#FF8C00"
    else:
        border_color = "#999"

    st.markdown(
        f'<div style="padding:12px 16px;background:#f8f9fa;border-left:5px solid {border_color};margin-bottom:4px;border-radius:8px;font-size:{fs_body}px;color:#333;">'
        f'{icon} {step["desc"]}  {bf_mark}'
        f'</div>',
        unsafe_allow_html=True,
    )

st.write("---")

# ─── 5. 교통약자 정보 ───
st.markdown("### ♿ 교통약자 시설 정보")

acc_cols = st.columns(min(len(ACCESSIBILITY_INFO), 3))
for idx, info in enumerate(ACCESSIBILITY_INFO[:3]):
    with acc_cols[idx]:
        status_color = "#4caf50" if info["status"] in ("정상 가동", "이용 가능") else "#ff9800"
        st.markdown(
            f'<div style="background:white;border:2px solid #e0e0e0;border-radius:12px;padding:14px;text-align:center;min-height:130px;">'
            f'<div style="font-size:28px;">{info["icon"]}</div>'
            f'<div style="font-size:{fs_small}px;font-weight:bold;margin-top:6px;">{info["station"]}</div>'
            f'<div style="font-size:{fs_badge}px;color:#666;">{info["facility"]}</div>'
            f'<div style="font-size:{fs_badge}px;color:{status_color};margin-top:4px;font-weight:bold;">{info["status"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

if len(ACCESSIBILITY_INFO) > 3:
    with st.expander(f"➕ 시설 정보 더보기 ({len(ACCESSIBILITY_INFO) - 3}개)"):
        for info in ACCESSIBILITY_INFO[3:]:
            st.markdown(f"**{info['icon']} {info['station']}** - {info['facility']} ({info['status']})")

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
col1, col2 = st.columns(2)
with col1:
    if st.button("🔊 음성 안내", use_container_width=True):
        st.toast("음성 안내를 시작합니다")
with col2:
    if st.button("📤 보호자 공유", use_container_width=True):
        st.toast("보호자에게 경로를 공유했습니다")
