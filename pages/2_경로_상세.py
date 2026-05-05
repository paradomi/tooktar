"""경로 상세 화면 - 지도, 교통약자 정보, AI 브리핑"""

import streamlit as st
import streamlit.components.v1 as components
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from components.styles import apply_global_styles
from components.header import render_header
from data.dummy_data import ROUTE_RESULTS, ACCESSIBILITY_INFO, AI_BRIEFING, ROUTE_STEPS, ROUTE_PATH

st.set_page_config(page_title="경로 상세", page_icon="🗺️", layout="centered")

apply_global_styles()

# 뒤로가기
if st.button("← 경로 목록", key="back_routes"):
    st.switch_page("pages/1_경로_탐색.py")

render_header()

# ─── 1. 지도 영역 (현재는 더미) ───
st.markdown("### 🗺️ 경로 지도")

route_id = st.session_state.get("selected_route_id", 1)
selected = next((r for r in ROUTE_RESULTS if r["id"] == route_id), ROUTE_RESULTS[0])

KAKAO_API_KEY = os.environ.get("KAKAO_JS_API_KEY", "")

if not KAKAO_API_KEY:
    st.warning("카카오맵 API 키가 설정되지 않았습니다. `.env` 파일에 `KAKAO_JS_API_KEY`를 추가해주세요.")

steps_json = json.dumps(ROUTE_STEPS, ensure_ascii=False)
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

var typeIcons = {{
    'walk': 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
    'bus': 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
    'transfer': 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
    'subway': 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png'
}};

var typeLabels = {{
    'walk': '🚶', 'bus': '🚌', 'transfer': '🔄', 'subway': '🚇'
}};

var bounds = new kakao.maps.LatLngBounds();

steps.forEach(function(step, i) {{
    var pos = new kakao.maps.LatLng(step.lat, step.lng);
    bounds.extend(pos);

    var marker = new kakao.maps.Marker({{
        map: map,
        position: pos,
        image: new kakao.maps.MarkerImage(
            typeIcons[step.type] || typeIcons['walk'],
            new kakao.maps.Size(24, 35)
        )
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
    st.markdown(f"""
    <div style="
        padding: 12px 16px;
        background: #f8f9fa;
        border-left: 4px solid #1f77b4;
        margin-bottom: 8px;
        border-radius: 8px;
        font-size: 15px;
    ">
        {icon} {step['desc']}  {bf_mark}
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# ─── 2. 교통약자 정보 (가로 스크롤 카드) ───
st.markdown("### ♿ 교통약자 시설 정보")

# Streamlit은 가로 스크롤이 제한적 → columns로 대체
acc_cols = st.columns(min(len(ACCESSIBILITY_INFO), 3))
for idx, info in enumerate(ACCESSIBILITY_INFO[:3]):
    with acc_cols[idx]:
        status_color = "#4caf50" if info["status"] == "정상 가동" or info["status"] == "이용 가능" else "#ff9800"
        st.markdown(f"""
        <div style="
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 14px;
            text-align: center;
            min-height: 130px;
        ">
            <div style="font-size: 28px;">{info['icon']}</div>
            <div style="font-size: 13px; font-weight: bold; margin-top: 6px;">{info['station']}</div>
            <div style="font-size: 12px; color: #666;">{info['facility']}</div>
            <div style="font-size: 12px; color: {status_color}; margin-top: 4px; font-weight: bold;">
                {info['status']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# 나머지 정보는 expander로
if len(ACCESSIBILITY_INFO) > 3:
    with st.expander(f"➕ 시설 정보 더보기 ({len(ACCESSIBILITY_INFO) - 3}개)"):
        for info in ACCESSIBILITY_INFO[3:]:
            st.markdown(f"**{info['icon']} {info['station']}** - {info['facility']} ({info['status']})")

st.write("---")

# ─── 3. AI 요약 브리핑 ───
st.markdown("### 🤖 AI 경로 브리핑")
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
    border-left: 4px solid #ff9800;
    border-radius: 12px;
    padding: 18px;
    font-size: 16px;
    line-height: 1.6;
    color: #333;
">
{AI_BRIEFING.replace(chr(10), '<br><br>')}
</div>
""", unsafe_allow_html=True)

st.write("")

# ─── 액션 버튼 ───
col1, col2 = st.columns(2)
with col1:
    if st.button("🔊 음성 안내", use_container_width=True):
        st.toast("음성 안내를 시작합니다")
with col2:
    if st.button("📤 보호자 공유", use_container_width=True):
        st.toast("보호자에게 경로를 공유했습니다")