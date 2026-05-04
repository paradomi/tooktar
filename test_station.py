import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GBIS_API_KEY")

# 정류소명/번호 목록조회 테스트
url = f"https://apis.data.go.kr/6410000/busstationservice/v2/getBusStationListv2"

# params 방식
print("[1] params 방식")
r1 = requests.get(url, params={"serviceKey": API_KEY, "keyword": "수원역", "format": "json"}, timeout=5)
print(f"상태: {r1.status_code}")
print(r1.text[:500])

# 직접 URL 방식
print("\n[2] 직접 URL 방식")
r2 = requests.get(f"{url}?serviceKey={API_KEY}&keyword=수원역&format=json", timeout=5)
print(f"상태: {r2.status_code}")
print(r2.text[:500])

# XML로도 시도
print("\n[3] XML 방식")
r3 = requests.get(f"{url}?serviceKey={API_KEY}&keyword=수원역", timeout=5)
print(f"상태: {r3.status_code}")
print(r3.text[:500])
