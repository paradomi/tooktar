import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GBIS_API_KEY")

# 테스트용 정류장: 수원역 (정류장 ID 228000724)
STATION_ID = "228000724"

url = "http://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"
params = {
    "serviceKey": API_KEY,
    "stationId": STATION_ID,
    "format": "json"
}

response = requests.get(url, params=params)
print("상태 코드:", response.status_code)
print("응답 내용:")
print(response.text[:2000])  # 너무 길면 잘라서 출력