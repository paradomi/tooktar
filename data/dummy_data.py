"""더미 데이터 - 실제 API 연결 전 UI 확인용"""

RECENT_SEARCHES = [
    {"name": "수원시청", "address": "경기도 수원시 팔달구 효원로 241"},
    {"name": "아주대병원", "address": "경기도 수원시 영통구 월드컵로 164"},
    {"name": "수원역", "address": "경기도 수원시 팔달구 덕영대로 924"},
]

FAVORITE_PLACES = [
    {"icon": "🏠", "label": "집", "address": "경기도 수원시 영통구"},
    {"icon": "🏥", "label": "병원", "address": "아주대학교병원"},
    {"icon": "🛒", "label": "시장", "address": "못골종합시장"},
    {"icon": "👨‍👩‍👧", "label": "자녀 집", "address": "경기도 성남시"},
]

ROUTE_RESULTS = [
    {
        "id": 1,
        "total_minutes": 35,
        "transfers": 0,
        "barrier_free_score": 95,
        "is_step_free": True,
        "low_floor_arrival": "10분 후 도착",
        "low_floor_bus_no": "143",
        "summary": "단차 없는 직행 경로",
    },
    {
        "id": 2,
        "total_minutes": 28,
        "transfers": 1,
        "barrier_free_score": 70,
        "is_step_free": False,
        "low_floor_arrival": "4분 후 도착",
        "low_floor_bus_no": "7770",
        "summary": "빠른 환승 경로 (경사로 있음)",
    },
    {
        "id": 3,
        "total_minutes": 42,
        "transfers": 1,
        "barrier_free_score": 88,
        "is_step_free": True,
        "low_floor_arrival": "운행 정보 없음",
        "low_floor_bus_no": "5-2",
        "summary": "전 구간 엘리베이터 이용 가능",
    },
]

ACCESSIBILITY_INFO = [
    {"station": "A역 1번 출구", "facility": "엘리베이터", "status": "정상 가동", "icon": "🛗"},
    {"station": "A역 2번 출구", "facility": "휠체어 리프트", "status": "정상 가동", "icon": "♿"},
    {"station": "B역 환승통로", "facility": "엘리베이터", "status": "점검 중", "icon": "⚠️"},
    {"station": "B역 4번 출구", "facility": "엘리베이터", "status": "정상 가동", "icon": "🛗"},
    {"station": "도착지 인근", "facility": "장애인 화장실", "status": "이용 가능", "icon": "🚻"},
]

AI_BRIEFING = """이 경로는 **전 구간 엘리베이터 이용이 가능**하지만, B역 환승 시 통로 엘리베이터가 현재 점검 중입니다. 우회 경로로 4번 출구 엘리베이터를 이용하시면 약 3분이 추가 소요됩니다.

현재 접근 중인 **143번 버스는 저상버스**이며, 약 10분 후 출발 정류장에 도착할 예정입니다. 휠체어 탑승 공간이 확보되어 있습니다.

도착지 인근에는 장애인 화장실이 이용 가능합니다."""

ROUTE_STEPS = [
    {
        "step": 1, "type": "walk",
        "desc": "출발지에서 A 정류장까지 도보 3분",
        "barrier_free": True,
        "arrival": None,
    },
    {
        "step": 2, "type": "bus",
        "desc": "143번 버스 탑승 (15분)",
        "barrier_free": True,
        "arrival": {
            "route_name": "143",
            "route_type": "일반버스",
            "station_name": "영통구청 정류장",
            "arrival_1": {"time": "4분 후", "remaining_stops": 2, "plate_no": "경기 70바 9999"},
            "arrival_2": {"time": "12분 후", "remaining_stops": 5, "plate_no": "경기 70바 8888"},
        },
        "low_floor_arrival": {
            "route_name": "143",
            "route_type": "저상버스",
            "station_name": "영통구청 정류장",
            "arrival_1": {"time": "10분 후", "remaining_stops": 3, "plate_no": "경기 70바 1234"},
            "arrival_2": {"time": "22분 후", "remaining_stops": 8, "plate_no": "경기 70바 5678"},
        },
    },
    {
        "step": 3, "type": "transfer",
        "desc": "B역 환승 - 엘리베이터 이용",
        "barrier_free": True,
        "arrival": None,
    },
    {
        "step": 4, "type": "subway",
        "desc": "지하철 1호선 (8분)",
        "barrier_free": True,
        "arrival": {
            "route_name": "1호선",
            "route_type": "지하철",
            "station_name": "B역 (수원 방면)",
            "is_low_floor": True,
            "arrival_1": {"time": "3분 후", "remaining_stops": 1, "plate_no": None},
            "arrival_2": {"time": "11분 후", "remaining_stops": 4, "plate_no": None},
        },
    },
    {
        "step": 5, "type": "walk",
        "desc": "도착지까지 도보 2분",
        "barrier_free": True,
        "arrival": None,
    },
]

ROUTE_PATH = [
    {"lat": 37.2636, "lng": 127.0286},
    {"lat": 37.2642, "lng": 127.0300},
    {"lat": 37.2650, "lng": 127.0320},
    {"lat": 37.2665, "lng": 127.0370},
    {"lat": 37.2700, "lng": 127.0450},
    {"lat": 37.2720, "lng": 127.0480},
    {"lat": 37.2750, "lng": 127.0500},
    {"lat": 37.2770, "lng": 127.0470},
    {"lat": 37.2790, "lng": 127.0435},
]

STEP_COORDS = [
    {"lat": 37.2636, "lng": 127.0286},
    {"lat": 37.2650, "lng": 127.0320},
    {"lat": 37.2700, "lng": 127.0450},
    {"lat": 37.2750, "lng": 127.0500},
    {"lat": 37.2790, "lng": 127.0435},
]