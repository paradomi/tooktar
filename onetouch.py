import json
import os

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

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

    # Step 2: 정류장 검색
    st.markdown("**① 정류장 검색**")
    keyword = st.text_input("정류장 이름을 입력하세요", placeholder="예: 수원역, 아주대, 신일아파트")

    if keyword:
        if st.button("🔍 검색", key="search_station"):
            with st.spinner("정류장 검색 중..."):
                body = api_get("busstationservice", "getBusStationListv2", {"keyword": keyword})
                if body:
                    items = body.get("busStationList", [])
                    if isinstance(items, dict):
                        items = [items]
                    st.session_state.search_stations = items
                else:
                    st.session_state.search_stations = []
                for k in ["selected_station", "station_routes"]:
                    st.session_state.pop(k, None)

    if "search_stations" in st.session_state:
        stations = st.session_state.search_stations
        if not stations:
            st.warning("검색 결과가 없습니다.")
        else:
            station_options = {
                f"{s.get('stationName', '')} ({s.get('mobileNo', '').strip()})": s
                for s in stations
            }
            sel_label = st.selectbox(
                f"검색 결과 ({len(stations)}건)",
                list(station_options.keys()),
            )
            sel_station = station_options[sel_label]

            if st.button("이 정류장 선택", key="pick_station"):
                st.session_state.selected_station = sel_station
                with st.spinner("경유 노선 조회 중..."):
                    body = api_get("busstationservice", "getBusStationViaRouteListv2",
                                   {"stationId": sel_station["stationId"]})
                    if body:
                        routes = body.get("busRouteList", [])
                        if isinstance(routes, dict):
                            routes = [routes]
                        st.session_state.station_routes = routes
                    else:
                        st.session_state.station_routes = []
                st.rerun()

    # Step 3: 노선 선택 & 저장
    if "selected_station" in st.session_state:
        station = st.session_state.selected_station
        st.success(f"선택된 정류장: **{station.get('stationName', '')}**")

        st.markdown("**② 노선 선택**")
        routes = st.session_state.get("station_routes", [])
        if not routes:
            st.warning("이 정류장의 노선 정보를 가져올 수 없습니다.")
        else:
            route_options = {
                f"{r.get('routeName', '')}번 ({r.get('regionName', '')})": r
                for r in routes
            }
            sel_route_label = st.selectbox(
                f"경유 노선 ({len(routes)}건)",
                list(route_options.keys()),
            )
            sel_route = route_options[sel_route_label]

            if st.button("✅ 이 장소 저장", use_container_width=True):
                if not name:
                    st.error("장소 이름을 입력해주세요.")
                else:
                    locations.append({
                        "name": name,
                        "icon": icon,
                        "stationId": str(station["stationId"]),
                        "stationName": station.get("stationName", ""),
                        "routeId": str(sel_route["routeId"]),
                        "routeName": str(sel_route.get("routeName", "")),
                        "staOrder": sel_route.get("staOrder", 1),
                        "x": station.get("x", 0),
                        "y": station.get("y", 0),
                    })
                    save_locations(locations)
                    for k in ["search_stations", "selected_station", "station_routes"]:
                        st.session_state.pop(k, None)
                    st.success(f"'{name}' 장소가 추가되었습니다!")
                    st.rerun()

    st.write("---")
    if st.button("← 메인으로 돌아가기", use_container_width=True):
        for k in ["search_stations", "selected_station", "station_routes"]:
            st.session_state.pop(k, None)
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

        # 지도 표시 (folium)
        loc_x = loc.get("x", 0)
        loc_y = loc.get("y", 0)
        if loc_x and loc_y:
            station_name = loc.get("stationName", "")
            m = folium.Map(location=[loc_y, loc_x], zoom_start=16)
            folium.Marker(
                [loc_y, loc_x],
                popup=station_name,
                tooltip=f"🚏 {station_name}",
                icon=folium.Icon(color="blue", icon="bus", prefix="fa"),
            ).add_to(m)
            st_folium(m, height=350, use_container_width=True)

            # 카카오맵 길안내 링크
            kakao_url = f"https://map.kakao.com/link/to/{station_name},{loc_y},{loc_x}"
            st.markdown(
                f'<a href="{kakao_url}" target="_blank" style="'
                f'display:block;text-align:center;padding:14px;margin-top:8px;'
                f'background:#FEE500;color:#3C1E1E;border-radius:12px;'
                f'text-decoration:none;font-weight:bold;font-size:18px;">'
                f'🗺️ 카카오맵 길안내</a>',
                unsafe_allow_html=True,
            )

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
