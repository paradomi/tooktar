"""경로 상세 화면 - ODsay mapObj 기반 실제 경로 + folium 지도 + 교통약자 정보"""

import streamlit as st
import streamlit.components.v1 as components
import folium
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

# ─── 2. folium 지도에 폴리라인 렌더링 ───
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
                        coords.append([float(pt["y"]), float(pt["x"])])
                    except (KeyError, ValueError, TypeError):
                        pass
            elif isinstance(graph_pos, str) and graph_pos:
                for pt in graph_pos.split(" "):
                    parts = pt.split(",")
                    if len(parts) == 2:
                        try:
                            coords.append([float(parts[1]), float(parts[0])])
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
            walk_lines.append([[float(sy), float(sx)], [float(ey), float(ex)]])

origin_coord = st.session_state.get("origin_coord", {})
dest_coord = st.session_state.get("dest_coord", {})

all_points = []
for sec in lane_sections:
    all_points.extend(sec["coords"])
for wl in walk_lines:
    all_points.extend(wl)
if origin_coord:
    all_points.append([origin_coord.get("lat", 0), origin_coord.get("lng", 0)])
if dest_coord:
    all_points.append([dest_coord.get("lat", 0), dest_coord.get("lng", 0)])

if not all_points:
    all_points = [[37.27, 127.03]]

center_lat = sum(p[0] for p in all_points) / len(all_points)
center_lng = sum(p[1] for p in all_points) / len(all_points)

origin_name = origin_coord.get("name", "출발") if origin_coord else "출발"
dest_name = dest_coord.get("name", "도착") if dest_coord else "도착"
origin_lat = origin_coord.get("lat", center_lat)
origin_lng = origin_coord.get("lng", center_lng)
dest_lat = dest_coord.get("lat", center_lat)
dest_lng = dest_coord.get("lng", center_lng)

m = folium.Map(location=[center_lat, center_lng], zoom_start=14, tiles="OpenStreetMap")

for sec in lane_sections:
    folium.PolyLine(
        locations=sec["coords"],
        color=sec["color"],
        weight=6,
        opacity=0.85,
    ).add_to(m)

for wl in walk_lines:
    folium.PolyLine(
        locations=wl,
        color="#FF8C00",
        weight=4,
        opacity=0.7,
        dash_array="10 6",
    ).add_to(m)

folium.Marker(
    location=[origin_lat, origin_lng],
    popup=origin_name,
    icon=folium.Icon(color="blue", icon="play", prefix="fa"),
    tooltip=f"🚩 {origin_name}",
).add_to(m)

folium.Marker(
    location=[dest_lat, dest_lng],
    popup=dest_name,
    icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    tooltip=f"📍 {dest_name}",
).add_to(m)

if all_points:
    m.fit_bounds(all_points, padding=[30, 30])

map_html = m._repr_html_()
components.html(map_html, height=450)

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
