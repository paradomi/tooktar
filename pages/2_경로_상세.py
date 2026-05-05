"""경로 상세 화면 - 지도, 교통약자 정보, AI 브리핑"""

import streamlit as st
import streamlit.components.v1 as components
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from components.styles import apply_global_styles, FONT_SIZE_PRESETS
from components.header import render_header
from data.dummy_data import ROUTE_RESULTS, ACCESSIBILITY_INFO, AI_BRIEFING, ROUTE_STEPS, ROUTE_PATH, STEP_COORDS

st.set_page_config(page_title="경로 상세", page_icon="🗺️", layout="centered")

apply_global_styles()

# 폰트 크기 프리셋 가져오기
level = st.session_state.get("font_size_level", "보통")
f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["보통"])
fs_body = f["body"]
fs_small = max(fs_body - 4, 12)
fs_badge = max(fs_body - 6, 11)
fs_title = f["h3"]

# 뒤로가기
if st.button("← 경로 목록", key="back_routes"):
    st.switch_page("pages/1_경로_탐색.py")

render_header()

# ─── 1. 지도 영역 (현재는 더미) ───
st.markdown("### 🗺️ 경로 지도")

route_id = st.session_state.get("selected_route_id", 1)
selected = next((r for r in ROUTE_RESULTS if r["id"] == route_id), ROUTE_RESULTS[0])

KAKAO_API_KEY = os.environ.get("KAKAO_JS_KEY", "")

if not KAKAO_API_KEY:
    st.warning("카카오맵 API 키가 설정되지 않았습니다. `.env` 파일에 `KAKAO_JS_KEY`를 추가해주세요.")

steps_for_map = []
for i, step in enumerate(ROUTE_STEPS):
    coord = STEP_COORDS[i] if i < len(STEP_COORDS) else STEP_COORDS[-1]
    steps_for_map.append({
        "type": step["type"],
        "desc": step["desc"],
        "barrier_free": step["barrier_free"],
        "lat": coord["lat"],
        "lng": coord["lng"],
    })

steps_json = json.dumps(steps_for_map, ensure_ascii=False)
path_json = json.dumps(ROUTE_PATH, ensure_ascii=False)

kakao_map_html = f"""
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_API_KEY}"></script>
<style>
  body {{ margin: 0; padding: 0; }}
  #map {{ width: 100%; height: 400px; border-radius: 16px; }}
</style>
</head><body>
<div id="map"></div>
<script>
var container = document.getElementById('map');
var steps = {steps_json};
var pathData = {path_json};

var centerLat = pathData.reduce(function(s, p) {{ return s + p.lat; }}, 0) / pathData.length;
var centerLng = pathData.reduce(function(s, p) {{ return s + p.lng; }}, 0) / pathData.length;

var options = {{
    center: new kakao.maps.LatLng(centerLat, centerLng),
    level: 5
}};
var map = new kakao.maps.Map(container, options);

var linePath = pathData.map(function(p) {{
    return new kakao.maps.LatLng(p.lat, p.lng);
}});

var polyline = new kakao.maps.Polyline({{
    path: linePath,
    strokeWeight: 5,
    strokeColor: '#1f77b4',
    strokeOpacity: 0.8,
    strokeStyle: 'solid'
}});
polyline.setMap(map);

var typeLabels = {{
    'walk': '🚶', 'bus': '🚌', 'transfer': '🔄', 'subway': '🚇'
}};

var bounds = new kakao.maps.LatLngBounds();

steps.forEach(function(step, i) {{
    var pos = new kakao.maps.LatLng(step.lat, step.lng);
    bounds.extend(pos);

    var marker = new kakao.maps.Marker({{
        map: map,
        position: pos
    }});

    var label = typeLabels[step.type] || '';
    var bfMark = step.barrier_free ? '✅' : '⚠️';

    var infowindow = new kakao.maps.InfoWindow({{
        content: '<div style="padding:8px 12px;font-size:13px;min-width:160px;line-height:1.4;">'
            + '<b>' + label + ' ' + step.desc + '</b><br>'
            + '배리어프리: ' + bfMark
            + '</div>'
    }});

    kakao.maps.event.addListener(marker, 'click', function() {{
        infowindow.open(map, marker);
    }});

    if (i === 0 || i === steps.length - 1) {{
        infowindow.open(map, marker);
    }}
}});

map.setBounds(bounds);
</script>
</body></html>
"""

components.html(kakao_map_html, height=420)

# ─── 경로 단계별 정보 ───
st.markdown(f"### 📋 {selected['total_minutes']}분 · {selected['summary']}")

for step in ROUTE_STEPS:
    icon = {"walk": "🚶", "bus": "🚌", "transfer": "🔄", "subway": "🚇"}.get(step["type"], "•")
    bf_mark = "✅" if step["barrier_free"] else "⚠️"

    # 구간 카드 색상
    border_color = "#1f77b4"
    if step["type"] == "bus":
        border_color = "#43a047"
    elif step["type"] == "subway":
        border_color = "#1565c0"
    elif step["type"] == "transfer":
        border_color = "#ff9800"

    st.markdown(
        f'<div style="padding:12px 16px;background:#f8f9fa;border-left:4px solid {border_color};margin-bottom:4px;border-radius:8px;font-size:{fs_body}px;">'
        f'{icon} {step["desc"]}  {bf_mark}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 대중교통 도착 정보 카드 (일반)
    arr = step.get("arrival")
    if arr:
        a1 = arr["arrival_1"]
        a2 = arr.get("arrival_2")

        plate1_html = f' · {a1["plate_no"]}' if a1.get("plate_no") else ""

        row2_html = ""
        if a2:
            plate2_html = f' · {a2["plate_no"]}' if a2.get("plate_no") else ""
            row2_html = (
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;color:#888;font-size:{fs_small}px;">'
                f'<span>다음 차량</span>'
                f'<span>{a2["time"]} · {a2["remaining_stops"]}정거장 전{plate2_html}</span>'
                f'</div>'
            )

        card_html = (
            f'<div style="background:white;border:2px solid {border_color};border-radius:12px;padding:14px 16px;margin-bottom:4px;margin-left:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
            f'<span style="font-weight:bold;font-size:{fs_title}px;">{icon} {arr["route_name"]} <span style="font-size:{fs_badge}px;color:#888;font-weight:normal;margin-left:4px;">{arr["route_type"]}</span></span>'
            f'</div>'
            f'<div style="font-size:{fs_small}px;color:#666;margin-bottom:8px;">📍 {arr["station_name"]}</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#f0f7ff;border-radius:8px;font-size:{fs_body}px;font-weight:bold;color:#1565c0;">'
            f'<span>🔜 곧 도착</span>'
            f'<span>{a1["time"]} · {a1["remaining_stops"]}정거장 전{plate1_html}</span>'
            f'</div>'
            f'{row2_html}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    # 저상버스 도착 정보 (설정이 켜져 있고 & 해당 구간에 데이터가 있을 때)
    show_low_floor = st.session_state.get("show_low_floor", True)
    lf = step.get("low_floor_arrival")
    if show_low_floor and lf:
        with st.expander("♿ 저상버스 정보 보기"):
            la1 = lf["arrival_1"]
            la2 = lf.get("arrival_2")

            lp1 = f' · {la1["plate_no"]}' if la1.get("plate_no") else ""

            lrow2 = ""
            if la2:
                lp2 = f' · {la2["plate_no"]}' if la2.get("plate_no") else ""
                lrow2 = (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;color:#888;font-size:{fs_small}px;">'
                    f'<span>다음 차량</span>'
                    f'<span>{la2["time"]} · {la2["remaining_stops"]}정거장 전{lp2}</span>'
                    f'</div>'
                )

            lf_card = (
                f'<div style="background:#f1f8e9;border:2px solid #66bb6a;border-radius:12px;padding:14px 16px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
                f'<span style="font-weight:bold;font-size:{fs_title}px;">♿ {lf["route_name"]} <span style="font-size:{fs_badge}px;color:#2e7d32;font-weight:normal;margin-left:4px;">{lf["route_type"]}</span></span>'
                f'<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;font-size:{fs_badge}px;font-weight:bold;">♿ 저상</span>'
                f'</div>'
                f'<div style="font-size:{fs_small}px;color:#666;margin-bottom:8px;">📍 {lf["station_name"]}</div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#e8f5e9;border-radius:8px;font-size:{fs_body}px;font-weight:bold;color:#2e7d32;">'
                f'<span>🔜 곧 도착</span>'
                f'<span>{la1["time"]} · {la1["remaining_stops"]}정거장 전{lp1}</span>'
                f'</div>'
                f'{lrow2}'
                f'</div>'
            )
            st.markdown(lf_card, unsafe_allow_html=True)

st.write("---")

# ─── 2. 교통약자 정보 (가로 스크롤 카드) ───
st.markdown("### ♿ 교통약자 시설 정보")

# Streamlit은 가로 스크롤이 제한적 → columns로 대체
acc_cols = st.columns(min(len(ACCESSIBILITY_INFO), 3))
for idx, info in enumerate(ACCESSIBILITY_INFO[:3]):
    with acc_cols[idx]:
        status_color = "#4caf50" if info["status"] == "정상 가동" or info["status"] == "이용 가능" else "#ff9800"
        st.markdown(
            f'<div style="background:white;border:2px solid #e0e0e0;border-radius:12px;padding:14px;text-align:center;min-height:130px;">'
            f'<div style="font-size:28px;">{info["icon"]}</div>'
            f'<div style="font-size:{fs_small}px;font-weight:bold;margin-top:6px;">{info["station"]}</div>'
            f'<div style="font-size:{fs_badge}px;color:#666;">{info["facility"]}</div>'
            f'<div style="font-size:{fs_badge}px;color:{status_color};margin-top:4px;font-weight:bold;">{info["status"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# 나머지 정보는 expander로
if len(ACCESSIBILITY_INFO) > 3:
    with st.expander(f"➕ 시설 정보 더보기 ({len(ACCESSIBILITY_INFO) - 3}개)"):
        for info in ACCESSIBILITY_INFO[3:]:
            st.markdown(f"**{info['icon']} {info['station']}** - {info['facility']} ({info['status']})")

st.write("---")

# ─── 3. AI 요약 브리핑 ───
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