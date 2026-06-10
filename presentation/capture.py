"""툭 타 앱 주요 화면 캡처 (발표자료용)"""
import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screens")
os.makedirs(OUT, exist_ok=True)
URL = "http://localhost:8501"


def shot(page, name, full=True):
    path = os.path.join(OUT, name)
    page.screenshot(path=path, full_page=full)
    print("saved", path)


def wait_text(page, text, timeout=60000):
    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 440, "height": 950}, device_scale_factor=2)

    # 1) 홈 화면
    page.goto(URL, wait_until="networkidle", timeout=60000)
    wait_text(page, "자주 가는 곳")
    page.wait_for_timeout(2500)
    shot(page, "01_home.png")

    # 2) 병원 즐겨찾기 클릭 → 경로 탐색
    page.get_by_role("button", name="🏥 병원").click()
    # 경로 카드(이 경로로 안내받기) 뜰 때까지 대기
    wait_text(page, "이 경로로 안내받기", timeout=90000)
    page.wait_for_timeout(3500)
    shot(page, "02_routes.png")

    # 3) 첫 경로 상세
    page.get_by_role("button", name="이 경로로 안내받기 →").first.click()
    page.wait_for_timeout(9000)  # 지도 + KRIC + 도보 로딩
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    shot(page, "03_detail.png")

    browser.close()
print("DONE")
