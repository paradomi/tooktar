import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GBIS_API_KEY")

# 노선번호목록조회
print("[1] 노선번호 검색 (keyword=13)")
r1 = requests.get(
    f"https://apis.data.go.kr/6410000/busrouteservice/v2/getBusRouteListv2?serviceKey={API_KEY}&keyword=13&format=json",
    timeout=5,
)
print(f"상태: {r1.status_code}")
print(r1.text[:500])

# 경유정류소목록조회
print("\n[2] 경유정류소 목록 (routeId=200000037)")
r2 = requests.get(
    f"https://apis.data.go.kr/6410000/busrouteservice/v2/getBusRouteStationListv2?serviceKey={API_KEY}&routeId=200000037&format=json",
    timeout=5,
)
print(f"상태: {r2.status_code}")
print(r2.text[:500])
