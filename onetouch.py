import json
import os

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_secret(key):
    """st.secrets (Cloud) 또는 os.getenv (로컬) 에서 키 읽기"""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)


API_KEY = get_secret("GBIS_API_KEY")
KAKAO_JS_KEY = get_secret("KAKAO_JS_KEY")
KAKAO_REST_KEY = get_secret("KAKAO_REST_KEY")
LOCATIONS_FILE = os.path.join(os.path.dirname(__file__), "locations.json")
API_BASE = "https://apis.data.go.kr/6410000"

ICONS = ["🏠", "🛒", "🏥", "👨‍👩‍👧", "🏢", "🏫", "⛪", "🏛️", "🌳", "🚉"]


def load_locations():
    if os.path.exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_locations(locations):
    with open(LOCATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)


def api_get(service, operation, params):
    url = f"{API_BASE}/{service}/v2/{operation}"
    params["serviceKey"] = API_KEY
    params["format"] = "json"
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data["response"]["msgHeader"]["resultCode"] != 0:
            return None
        return data["response"]["msgBody"]
    except Exception:
        return None


def kakao_search(keyword):
    """카카오 키워드로 장소 검색"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        r = requests.get(url, headers=headers, params={"query": keyword, "size": 10}, timeout=5)
        data = r.json()
        return data.get("documents", [])
    except Exception:
        return []


def find_nearby_stations(x, y):
    """좌표 주변 버스 정류장 검색 (카카오 카테고리 검색)"""
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        r = requests.get(url, headers=headers, params={
            "category_group_code": "BK9",  # 버스정류장은 없으므로 대체 방법 사용
            "x": x, "y": y,
            "radius": 500,
            "sort": "distance",
        }, timeout=5)
        return r.json().get("documents", [])
    except Exception:
        return []


def search_routes(keyword):
    body = api_get("busrouteservice", "getBusRouteListv2", {"keyword": keyword})
    if not body:
        return []
    items = body.get("busRouteList", [])
    if isinstance(items, dict):
        items = [items]
    return items


def get_route_stations(route_id):
    body = api_get("busrouteservice", "getBusRouteStationListv2", {"routeId": route_id})
    if not body:
        return []
    items = body.get("busRouteStationList", [])
    if isinstance(items, dict):
        items = [items]
    return items


def get_bus_arrival(station_id, route_id):
    body = api_get("busarrivalservice", "getBusArrivalItemv2", {
        "stationId": station_id,
        "routeId": route_id,
    })
    if not body:
        return None
    return body.get("busArrivalItem")


st.set_page_config(page_title="원터치 모빌리티", page_icon="🚌", layout="centered")

st.markdown("""
<style>
    .stButton > button {
        height: 140px;
        font-size: 28px !important;
        font-weight: bold;
        border-radius: 20px;
        border: 3px solid #1f77b4;
    }
    .stButton > button:hover {
        background-color: #1f77b4;
        color: white;
    }
    h1 { font-size: 48px !important; text-align: center; }
    h3 { font-size: 32px !important; text-align: center; margin-top: 30px; }
    .stAlert { font-size: 24px !important; padding: 20px !important; }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "main"

# ── 설정 페이지 ──
if st.session_state.page == "settings":
    st.title("⚙️ 장소 설정")

    locations = load_locations()

    st.markdown("### 등록된 장소")
    if not locations:
        st.info("등록된 장소가 없습니다.")
    for i, loc in enumerate(locations):
        col_info, col_del = st.columns([4, 1])
        with col_info:
            st.write(f"**{loc['icon']} {loc['name']}** — {loc.get('stationName', '')} / {loc.get('routeName', '')}번")
        with col_del:
            if st.button("삭제", key=f"del_{i}"):
                locations.pop(i)
                save_locations(locations)
                st.rerun()

    st.write("---")
    st.markdown("### 새 장소 추가")

    # Step 1: 장소 이름 & 아이콘
    col_name, col_icon = st.columns([3, 1])
    with col_name:
        name = st.text_input("장소 이름", placeholder="예: 집, 병원, 시장")
    with col_icon:
        icon = st.selectbox("아이콘", ICONS)

    # Step 2: 카카오맵 장소 검색
    st.markdown("**① 장소 검색**")
    keyword = st.text_input("장소를 검색하세요", placeholder="예: 수원역, 아주대학교, 이마트 수원점")

    if keyword:
        if st.button("🔍 검색", key="search_place"):
            with st.spinner("장소 검색 중..."):
                st.session_state.kakao_results = kakao_search(keyword)
                for key in ["selected_place", "nearby_routes", "selected_nearby"]:
                    st.session_state.pop(key, None)

    if "kakao_results" in st.session_state and st.session_state.kakao_results:
        places = st.session_state.kakao_results
        place_options = {
            f"{p.get('place_name', '')} — {p.get('address_name', '')}": p
            for p in places
        }
        selected_place_label = st.selectbox(
            f"검색 결과 ({len(places)}건)",
            list(place_options.keys()),
        )
        selected_place = place_options[selected_place_label]

        if st.button("이 장소 선택", key="select_place"):
            st.session_state.selected_place = selected_place
            # 주변 버스 정류장 검색 (경기 버스 API로 조회)
            with st.spinner("주변 정류장 및 노선 조회 중..."):
                px = float(selected_place["x"])
                py = float(selected_place["y"])
                # 버스도착정보 목록으로 주변 정류장 찾기 — 카카오 카테고리 검색 사용
                url = "https://dapi.kakao.com/v2/local/search/keyword.json"
                headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
                r = requests.get(url, headers=headers, params={
                    "query": "버스정류장",
                    "x": px, "y": py,
                    "radius": 500,
                    "sort": "distance",
                    "size": 5,
                }, timeout=5)
                kakao_stations = r.json().get("documents", [])

                # 카카오 정류장 이름으로 GBIS에서 노선 검색
                nearby_list = []
                seen_stations = set()
                for ks in kakao_stations:
                    station_name = ks.get("place_name", "").replace("버스정류장", "").replace("정류장", "").strip()
                    if not station_name or station_name in seen_stations:
                        continue
                    seen_stations.add(station_name)
                    # GBIS 정류소 검색 시도
                    body = api_get("busstationservice", "getBusStationListv2", {"keyword": station_name})
                    if not body:
                        continue
                    stations = body.get("busStationList", [])
                    if isinstance(stations, dict):
                        stations = [stations]
                    # 가장 가까운 정류장 찾기
                    for s in stations:
                        sx, sy = float(s.get("x", 0)), float(s.get("y", 0))
                        dist = ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5
                        if dist < 0.006:  # 약 500m 이내
                            nearby_list.append({
                                "stationId": s["stationId"],
                                "stationName": s.get("stationName", ""),
                                "x": sx,
                                "y": sy,
                                "distance": ks.get("distance", ""),
                            })

                # 중복 제거
                unique = {}
                for s in nearby_list:
                    unique[s["stationId"]] = s
                st.session_state.nearby_stations = list(unique.values())
            st.rerun()

    # Step 3: 주변 정류장 선택 → 노선 선택
    if "selected_place" in st.session_state:
        place = st.session_state.selected_place
        st.success(f"선택된 장소: **{place.get('place_name', '')}**")

        st.markdown("**② 주변 정류장 선택**")
        nearby = st.session_state.get("nearby_stations", [])
        if not nearby:
            st.warning("주변 500m 이내 정류장을 찾을 수 없습니다.")
            st.markdown("**버스 번호로 직접 검색**")
            route_keyword = st.text_input("버스 번호 입력", placeholder="예: 13, 720")
            if route_keyword and st.button("🔍 노선 검색", key="fallback_route"):
                with st.spinner("노선 검색 중..."):
                    st.session_state.fallback_routes = search_routes(route_keyword)
                    st.rerun()
            if "fallback_routes" in st.session_state and st.session_state.fallback_routes:
                fb_routes = st.session_state.fallback_routes
                fb_options = {f"{r.get('routeName', '')}번 ({r.get('regionName', '')})": r for r in fb_routes}
                fb_label = st.selectbox("노선 선택", list(fb_options.keys()))
                fb_route = fb_options[fb_label]
                if st.button("이 노선 선택", key="fb_select"):
                    st.session_state.fallback_selected_route = fb_route
                    with st.spinner("정류장 목록 조회 중..."):
                        st.session_state.fallback_stations = get_route_stations(fb_route["routeId"])
                    st.rerun()
                if "fallback_stations" in st.session_state:
                    fb_sts = st.session_state.fallback_stations
                    fb_st_options = {
                        f"{s.get('stationSeq', '')}. {s.get('stationName', '')} ({s.get('regionName', '')})": s
                        for s in fb_sts
                    }
                    fb_st_label = st.selectbox("정류장 선택", list(fb_st_options.keys()))
                    fb_station = fb_st_options[fb_st_label]
                    fb_route = st.session_state.fallback_selected_route
                    if st.button("✅ 이 장소 저장", use_container_width=True, key="fb_save"):
                        if not name:
                            st.error("장소 이름을 입력해주세요.")
                        else:
                            locations.append({
                                "name": name,
                                "icon": icon,
                                "stationId": str(fb_station["stationId"]),
                                "stationName": fb_station.get("stationName", ""),
                                "routeId": str(fb_route["routeId"]),
                                "routeName": str(fb_route.get("routeName", "")),
                                "staOrder": fb_station.get("stationSeq", 1),
                                "x": fb_station.get("x", 0),
                                "y": fb_station.get("y", 0),
                            })
                            save_locations(locations)
                            for key in ["kakao_results", "selected_place", "nearby_stations",
                                        "fallback_routes", "fallback_selected_route", "fallback_stations"]:
                                st.session_state.pop(key, None)
                            st.success(f"'{name}' 장소가 추가되었습니다!")
                            st.rerun()
        else:
            station_options = {
                f"{s.get('stationName', '')} ({s.get('distance', '')}m)": s
                for s in nearby
            }
            selected_station_label = st.selectbox(
                f"주변 정류장 ({len(nearby)}개)",
                list(station_options.keys()),
            )
            selected_station = station_options[selected_station_label]

            if st.button("이 정류장 선택", key="select_nearby"):
                st.session_state.selected_nearby = selected_station
                # 이 정류장의 경유 노선 조회
                with st.spinner("경유 노선 조회 중..."):
                    body = api_get("busstationservice", "getBusStationViaRouteListv2",
                                   {"stationId": selected_station["stationId"]})
                    if body:
                        routes = body.get("busRouteList", [])
                        if isinstance(routes, dict):
                            routes = [routes]
                        st.session_state.nearby_routes = routes
                    else:
                        st.session_state.nearby_routes = []
                st.rerun()

        # Step 4: 노선 선택 및 저장
        if "selected_nearby" in st.session_state:
            station = st.session_state.selected_nearby
            st.info(f"선택된 정류장: **{station.get('stationName', '')}**")

            st.markdown("**③ 노선 선택**")
            routes = st.session_state.get("nearby_routes", [])
            if not routes:
                st.warning("이 정류장의 노선 정보를 가져올 수 없습니다.")
            else:
                route_options = {
                    f"{r.get('routeName', '')}번 ({r.get('regionName', '')})": r
                    for r in routes
                }
                selected_route_label = st.selectbox(
                    f"경유 노선 ({len(routes)}건)",
                    list(route_options.keys()),
                )
                selected_route = route_options[selected_route_label]

                if st.button("✅ 이 장소 저장", use_container_width=True):
                    if not name:
                        st.error("장소 이름을 입력해주세요.")
                    else:
                        locations.append({
                            "name": name,
                            "icon": icon,
                            "stationId": str(station["stationId"]),
                            "stationName": station.get("stationName", ""),
                            "routeId": str(selected_route["routeId"]),
                            "routeName": str(selected_route.get("routeName", "")),
                            "staOrder": selected_route.get("staOrder", 1),
                            "x": station.get("x", 0),
                            "y": station.get("y", 0),
                        })
                        save_locations(locations)
                        for key in ["kakao_results", "selected_place", "nearby_stations",
                                    "selected_nearby", "nearby_routes"]:
                            st.session_state.pop(key, None)
                        st.success(f"'{name}' 장소가 추가되었습니다!")
                        st.rerun()

    st.write("---")
    if st.button("← 메인으로 돌아가기", use_container_width=True):
        for key in ["kakao_results", "selected_place", "nearby_stations",
                    "selected_nearby", "nearby_routes",
                    "fallback_routes", "fallback_selected_route", "fallback_stations"]:
            st.session_state.pop(key, None)
        st.session_state.page = "main"
        st.rerun()

# ── 메인 페이지 ──
else:
    st.title("🚌 원터치 모빌리티")
    st.markdown(
        "<p style='text-align: center; font-size: 20px; color: gray;'>"
        "교통약자를 위한 한 버튼 대중교통 앱</p>",
        unsafe_allow_html=True,
    )

    st.write("---")
    st.markdown("### 어디로 가시나요?")
    st.write("")

    locations = load_locations()

    if not locations:
        st.info("등록된 장소가 없습니다. 설정에서 장소를 추가해주세요.")
    else:
        rows = [locations[i:i + 2] for i in range(0, len(locations), 2)]
        for row in rows:
            cols = st.columns(2)
            for j, loc in enumerate(row):
                with cols[j]:
                    if st.button(
                        f"{loc['icon']}\n\n{loc['name']}",
                        use_container_width=True,
                        key=f"loc_{loc['name']}_{j}",
                    ):
                        st.session_state.selected = loc
            st.write("")

    if "selected" in st.session_state and st.session_state.selected:
        loc = st.session_state.selected
        st.write("---")
        with st.spinner(f"{loc['name']} 도착 정보 조회 중..."):
            info = get_bus_arrival(loc["stationId"], loc["routeId"])

        if info and info.get("predictTime1"):
            low = " (저상버스)" if info.get("lowPlate1") else ""
            st.success(
                f"🚌 **{loc['name']}** 방면 {info.get('routeName', '')}번 버스\n\n"
                f"**{info['predictTime1']}분 후** 도착{low}"
            )
            if info.get("predictTime2"):
                st.info(f"다음 버스: **{info['predictTime2']}분 후** 도착")
        elif info:
            st.warning(f"🚌 {loc['name']} 방면 버스 운행 정보가 없습니다. (운행 종료 또는 미운행)")
        else:
            st.error("도착 정보를 가져올 수 없습니다.")

        # 카카오맵 + 앱 내 길안내
        loc_x = loc.get("x", 0)
        loc_y = loc.get("y", 0)
        if loc_x and loc_y and KAKAO_JS_KEY:
            station_name = loc.get("stationName", "").replace("'", "\\'")
            map_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
                    #map {{ width: 100%; height: 350px; border-radius: 15px; }}
                    #info-box {{
                        margin-top: 10px;
                        padding: 14px 18px;
                        background: #f0f4ff;
                        border-radius: 12px;
                        font-size: 16px;
                        line-height: 1.6;
                    }}
                    #info-box .title {{ font-weight: bold; font-size: 18px; margin-bottom: 6px; }}
                    #info-box .detail {{ color: #555; }}
                    #steps {{
                        margin-top: 10px;
                        padding: 0 4px;
                        max-height: 200px;
                        overflow-y: auto;
                    }}
                    .step {{
                        padding: 10px 14px;
                        margin: 4px 0;
                        background: white;
                        border-radius: 10px;
                        font-size: 15px;
                        border-left: 4px solid #3498db;
                    }}
                    #status {{ text-align: center; color: #888; font-size: 14px; margin-top: 8px; }}
                    #kakao-link {{
                        display: block;
                        text-align: center;
                        margin-top: 8px;
                        padding: 12px;
                        background: #FEE500;
                        color: #3C1E1E;
                        border-radius: 10px;
                        text-decoration: none;
                        font-weight: bold;
                        font-size: 16px;
                    }}
                </style>
                <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&autoload=false"></script>
            </head>
            <body>
                <div id="map"></div>
                <div id="info-box">
                    <div class="title">🚏 {station_name}</div>
                    <div class="detail" id="route-info">경로를 계산하는 중...</div>
                </div>
                <div id="steps"></div>
                <div id="status"></div>
                <a id="kakao-link" href="https://map.kakao.com/link/to/{station_name},{loc_y},{loc_x}" target="_blank" style="display:none;">
                    🗺️ 카카오맵에서 상세 보기
                </a>
                <script>
                    var destLat = {loc_y};
                    var destLng = {loc_x};
                    var REST_KEY = '{KAKAO_REST_KEY}';

                    kakao.maps.load(function() {{
                        var container = document.getElementById('map');
                        var map = new kakao.maps.Map(container, {{
                            center: new kakao.maps.LatLng(destLat, destLng),
                            level: 4
                        }});

                        // 목적지 마커
                        var destMarker = new kakao.maps.Marker({{
                            position: new kakao.maps.LatLng(destLat, destLng),
                            map: map
                        }});
                        var destInfo = new kakao.maps.InfoWindow({{
                            content: '<div style="padding:5px;font-size:13px;font-weight:bold;">🚏 {station_name}</div>'
                        }});
                        destInfo.open(map, destMarker);

                        if (!navigator.geolocation) {{
                            document.getElementById('route-info').innerText = '위치 기능을 지원하지 않는 브라우저입니다.';
                            return;
                        }}

                        navigator.geolocation.getCurrentPosition(function(pos) {{
                            var myLat = pos.coords.latitude;
                            var myLng = pos.coords.longitude;

                            // 내 위치 마커
                            var myImg = new kakao.maps.MarkerImage(
                                'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
                                new kakao.maps.Size(24, 35)
                            );
                            var myMarker = new kakao.maps.Marker({{
                                position: new kakao.maps.LatLng(myLat, myLng),
                                map: map,
                                image: myImg
                            }});
                            var myInfo = new kakao.maps.InfoWindow({{
                                content: '<div style="padding:5px;font-size:13px;color:#e74c3c;font-weight:bold;">📍 내 위치</div>'
                            }});
                            myInfo.open(map, myMarker);

                            // 카카오맵 링크 업데이트
                            var link = document.getElementById('kakao-link');
                            link.href = 'https://map.kakao.com/link/from/내위치,' + myLat + ',' + myLng +
                                        '/to/{station_name},' + destLat + ',' + destLng;
                            link.style.display = 'block';

                            // 카카오 모빌리티 도보 경로 API 호출
                            fetch('https://apis-navi.kakaomobility.com/v1/directions?origin=' +
                                myLng + ',' + myLat + '&destination=' + destLng + ',' + destLat +
                                '&priority=RECOMMEND', {{
                                headers: {{ 'Authorization': 'KakaoAK ' + REST_KEY }}
                            }})
                            .then(function(r) {{ return r.json(); }})
                            .then(function(data) {{
                                if (data.routes && data.routes[0] && data.routes[0].result_code === 0) {{
                                    var route = data.routes[0];
                                    var summary = route.summary;
                                    var dist = summary.distance;
                                    var dur = summary.duration;

                                    // 거리/시간 표시
                                    var distText = dist >= 1000 ? (dist/1000).toFixed(1) + 'km' : dist + 'm';
                                    var durMin = Math.ceil(dur / 60);
                                    document.getElementById('route-info').innerHTML =
                                        '🚶 도보 <b>' + distText + '</b> · 약 <b>' + durMin + '분</b>';

                                    // 경로 폴리라인 그리기
                                    var linePath = [];
                                    route.sections.forEach(function(section) {{
                                        section.roads.forEach(function(road) {{
                                            for (var i = 0; i < road.vertexes.length; i += 2) {{
                                                linePath.push(new kakao.maps.LatLng(road.vertexes[i+1], road.vertexes[i]));
                                            }}
                                        }});
                                    }});

                                    var polyline = new kakao.maps.Polyline({{
                                        path: linePath,
                                        strokeWeight: 5,
                                        strokeColor: '#3498db',
                                        strokeOpacity: 0.9,
                                        strokeStyle: 'solid'
                                    }});
                                    polyline.setMap(map);

                                    // 안내 단계 표시
                                    var stepsHtml = '';
                                    var stepNum = 1;
                                    route.sections.forEach(function(section) {{
                                        section.guides.forEach(function(guide) {{
                                            if (guide.name && guide.guidance) {{
                                                stepsHtml += '<div class="step">' + stepNum + '. ' +
                                                    guide.guidance + ' (' + guide.name + ')</div>';
                                                stepNum++;
                                            }}
                                        }});
                                    }});
                                    if (stepsHtml) {{
                                        document.getElementById('steps').innerHTML = stepsHtml;
                                    }}

                                    // 경로에 맞게 지도 영역 조정
                                    var bounds = new kakao.maps.LatLngBounds();
                                    linePath.forEach(function(p) {{ bounds.extend(p); }});
                                    map.setBounds(bounds);
                                }} else {{
                                    // 자동차 경로 실패시 직선 표시
                                    showStraightLine(map, myLat, myLng);
                                }}
                            }})
                            .catch(function(err) {{
                                showStraightLine(map, myLat, myLng);
                            }});

                            function showStraightLine(map, myLat, myLng) {{
                                var linePath = [
                                    new kakao.maps.LatLng(myLat, myLng),
                                    new kakao.maps.LatLng(destLat, destLng)
                                ];
                                var polyline = new kakao.maps.Polyline({{
                                    path: linePath,
                                    strokeWeight: 4,
                                    strokeColor: '#3498db',
                                    strokeOpacity: 0.7,
                                    strokeStyle: 'dashed'
                                }});
                                polyline.setMap(map);
                                var dist = Math.round(polyline.getLength());
                                var walkMin = Math.ceil(dist / 67);
                                var distText = dist >= 1000 ? (dist/1000).toFixed(1) + 'km' : dist + 'm';
                                document.getElementById('route-info').innerHTML =
                                    '🚶 직선 거리 <b>' + distText + '</b> · 도보 약 <b>' + walkMin + '분</b>';

                                var bounds = new kakao.maps.LatLngBounds();
                                bounds.extend(new kakao.maps.LatLng(myLat, myLng));
                                bounds.extend(new kakao.maps.LatLng(destLat, destLng));
                                map.setBounds(bounds);
                            }}
                        }}, function(err) {{
                            document.getElementById('route-info').innerText = '📍 위치 권한을 허용해주세요.';
                        }}, {{ enableHighAccuracy: true, timeout: 5000 }});
                    }});
                </script>
            </body>
            </html>
            """
            st.components.v1.html(map_html, height=650)

        if st.button("닫기"):
            del st.session_state.selected
            st.rerun()

    st.write("---")
    st.markdown("### 이용 모드")
    mode = st.radio(
        "이용 모드 선택",
        ["👵 어르신 모드", "♿ 휠체어 모드", "👶 유모차 모드", "🦯 시각장애 모드"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.caption(f"현재 모드: {mode}")

    st.write("")
    if st.button("⚙️ 장소 설정", use_container_width=True):
        st.session_state.page = "settings"
        st.rerun()
