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
from data.dummy_data import ROUTE_RESULTS, ACCESSIBILITY_INFO, AI_BRIEFING, ROUTE_STEPS
from data.odsay_api import search_pub_trans_path, build_route_segments

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

KAKAO_APP_KEY = os.environ.get("KAKAO_SDK_DOMAIN", "")

if not KAKAO_APP_KEY:
    st.warning("카카오맵 API 키가 설정되지 않았습니다. `.env` 파일에 `KAKAO_SDK_DOMAIN`을 추가해주세요.")

# ─── ODsay 대중교통 경로 조회 ───
origin_x, origin_y = 127.0286, 37.2636   # 출발지 (수원 영통)
dest_x, dest_y = 127.0435, 37.2790       # 도착지

cache_key = f"odsay_v6_{origin_x}_{origin_y}_{dest_x}_{dest_y}"
if cache_key not in st.session_state:
    with st.spinner("실제 대중교통 경로를 조회 중..."):
        path_result = search_pub_trans_path(origin_x, origin_y, dest_x, dest_y)
        if path_result and "result" in path_result:
            route_data = build_route_segments(path_result, origin_x, origin_y, dest_x, dest_y)
            st.session_state[cache_key] = route_data
        else:
            st.session_state[cache_key] = None

cached = st.session_state.get(cache_key)

if cached and KAKAO_APP_KEY:
    all_segments = cached.get("segments", [])
    markers = cached.get("markers", [])

    markers_json = json.dumps(markers, ensure_ascii=False)
    segments_json = json.dumps(all_segments, ensure_ascii=False)

    start_marker = json.dumps({"lat": origin_y, "lng": origin_x}, ensure_ascii=False)
    end_marker = json.dumps({"lat": dest_y, "lng": dest_x}, ensure_ascii=False)

    legend_items = []
    for seg in all_segments:
        if seg["type"] == "walk":
            label = f'🚶 {seg.get("desc", "도보")}'
            legend_items.append({"label": label, "color": "#FF8C00", "dash": True})
        else:
            color = seg.get("color", "#1f77b4")
            icon = "🚌" if seg["type"] == "bus" else "🚇"
            label = f'{icon} {seg.get("name", "") or seg.get("desc", "")}'
            legend_items.append({"label": label, "color": color, "dash": False})
    legend_json = json.dumps(legend_items, ensure_ascii=False)

    kakao_map_html = f"""
    <!DOCTYPE html>
    <html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      body {{ margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
      #map {{ width:100%; height:420px; border-radius:16px; }}
      #legend {{
        position:absolute; bottom:16px; left:16px; z-index:10;
        background:rgba(255,255,255,0.95); border-radius:10px;
        padding:10px 14px; box-shadow:0 2px 8px rgba(0,0,0,0.15);
        font-size:12px; line-height:1.8; max-width:220px;
      }}
      .leg-row {{ display:flex; align-items:center; gap:8px; }}
      .leg-line {{ width:28px; height:4px; border-radius:2px; flex-shrink:0; }}
      .leg-dash {{ background:repeating-linear-gradient(90deg,var(--c) 0,var(--c) 6px,transparent 6px,transparent 10px); }}
      .leg-solid {{ background:var(--c); }}
    </style>
    </head><body>
    <div style="position:relative;">
      <div id="map"></div>
      <div id="legend"></div>
    </div>
    <script>
    (function() {{
        var script = document.createElement('script');
        script.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_APP_KEY}&autoload=false';
        script.onload = function() {{
            kakao.maps.load(function() {{
                var segments = {segments_json};
                var markers = {markers_json};
                var startPt = {start_marker};
                var endPt = {end_marker};
                var legendData = {legend_json};

                var map = new kakao.maps.Map(document.getElementById('map'), {{
                    center: new kakao.maps.LatLng(startPt.lat, startPt.lng),
                    level: 5
                }});
                var bounds = new kakao.maps.LatLngBounds();

                segments.forEach(function(seg) {{
                    if (!seg.coords || seg.coords.length < 2) return;
                    var path = seg.coords.map(function(c) {{
                        var ll = new kakao.maps.LatLng(c.lat, c.lng);
                        bounds.extend(ll);
                        return ll;
                    }});
                    var sw, sc, so, ss;
                    if (seg.type === 'walk') {{
                        sw = 5; sc = '#FF8C00'; so = 0.9; ss = 'shortdash';
                    }} else {{
                        sw = 7; sc = seg.color || '#1f77b4'; so = 0.9; ss = 'solid';
                    }}
                    new kakao.maps.Polyline({{
                        path: path, strokeWeight: sw,
                        strokeColor: sc, strokeOpacity: so, strokeStyle: ss
                    }}).setMap(map);
                }});

                var startPos = new kakao.maps.LatLng(startPt.lat, startPt.lng);
                bounds.extend(startPos);
                var sm = new kakao.maps.Marker({{ map: map, position: startPos }});
                var siw = new kakao.maps.InfoWindow({{
                    content: '<div style="padding:6px 10px;font-size:13px;font-weight:bold;color:#d32f2f;">📍 출발</div>'
                }});
                siw.open(map, sm);

                var endPos = new kakao.maps.LatLng(endPt.lat, endPt.lng);
                bounds.extend(endPos);
                var em = new kakao.maps.Marker({{ map: map, position: endPos }});
                var eiw = new kakao.maps.InfoWindow({{
                    content: '<div style="padding:6px 10px;font-size:13px;font-weight:bold;color:#1565c0;">🏁 도착</div>'
                }});
                eiw.open(map, em);

                markers.forEach(function(mk) {{
                    var pos = new kakao.maps.LatLng(mk.lat, mk.lng);
                    bounds.extend(pos);
                    var marker = new kakao.maps.Marker({{
                        map: map, position: pos,
                        image: new kakao.maps.MarkerImage(
                            'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
                            new kakao.maps.Size(24, 35)
                        )
                    }});
                    var iw = new kakao.maps.InfoWindow({{
                        content: '<div style="padding:5px 10px;font-size:12px;white-space:nowrap;">' + mk.name + '</div>'
                    }});
                    kakao.maps.event.addListener(marker, 'click', function() {{ iw.open(map, marker); }});
                }});

                map.setBounds(bounds);

                var legendEl = document.getElementById('legend');
                var html = '<div style="font-weight:bold;margin-bottom:4px;">구간 안내</div>';
                legendData.forEach(function(item) {{
                    var cls = item.dash ? 'leg-dash' : 'leg-solid';
                    html += '<div class="leg-row">'
                        + '<div class="leg-line ' + cls + '" style="--c:' + item.color + ';"></div>'
                        + '<span>' + item.label + '</span></div>';
                }});
                legendEl.innerHTML = html;
            }});
        }};
        document.head.appendChild(script);
    }})();
    </script>
    </body></html>
    """
    components.html(kakao_map_html, height=460)

else:
    if not cached:
        st.error("ODsay 경로 조회에 실패했습니다. API 키를 확인해주세요.")
    st.markdown(
        '<div style="background:#e3f2fd;height:280px;border-radius:16px;display:flex;align-items:center;'
        'justify-content:center;color:#1565c0;font-size:16px;">🗺️ 지도를 불러올 수 없습니다</div>',
        unsafe_allow_html=True,
    )

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