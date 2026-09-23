"""대시보드 스크린샷 세트 캡처 (Playwright).

프리셋 4개 × 비중 2안 = 8장. 각 조합별로 사이드바 슬라이더를 조작한 뒤
전체 페이지를 figures/에서 figures/dashboard/에 캡처한다.

실행: streamlit 서버(8505)가 떠 있어야 함.
    python capture_dashboard.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8505"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures" / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)

ASSETS = ["SPY", "SHY", "TLT", "GLD", "BTC-USD"]
PRESET_ORDER = ["전체", "2008 금융위기", "2020 코로나", "2022 인플레이션"]

# (이름, 프리셋, {자산: 비중%})
SHOTS = [
    ("전체_6040",      "전체",            {"SPY": 60, "SHY": 0, "TLT": 40, "GLD": 0, "BTC-USD": 0}),
    ("전체_5자산",     "전체",            {"SPY": 50, "SHY": 15, "TLT": 15, "GLD": 15, "BTC-USD": 5}),
    ("2008금융위기_6040", "2008 금융위기", {"SPY": 60, "SHY": 0, "TLT": 40, "GLD": 0, "BTC-USD": 0}),
    ("2008금융위기_5자산","2008 금융위기", {"SPY": 50, "SHY": 15, "TLT": 15, "GLD": 15, "BTC-USD": 5}),
    ("2020코로나_6040",   "2020 코로나",   {"SPY": 60, "SHY": 0, "TLT": 40, "GLD": 0, "BTC-USD": 0}),
    ("2020코로나_5자산",  "2020 코로나",   {"SPY": 50, "SHY": 15, "TLT": 15, "GLD": 15, "BTC-USD": 5}),
    ("2022인플레이션_6040", "2022 인플레이션", {"SPY": 60, "SHY": 0, "TLT": 40, "GLD": 0, "BTC-USD": 0}),
    ("2022인플레이션_5자산",  "2022 인플레이션", {"SPY": 50, "SHY": 15, "TLT": 15, "GLD": 15, "BTC-USD": 5}),
]


def set_slider(page, asset: str, value: int):
    """Streamlit 슬라이더를 특정 값으로 설정 (input[type=range] 접근)."""
    # 각 슬라이더는 asset 라벨의 aria/접근성 이름으로 식별
    locator = page.locator(f'input[type="range"][aria-label="{asset}"]')
    if locator.count() == 0:
        # aria-label이 asset이 아니면 label 텍스트로
        locator = page.locator(f'[aria-label*="{asset}"]')
    handle = locator.first
    handle.evaluate(
        """(el, v) => {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, v);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        value,
    )


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})

        page.goto(URL, wait_until="networkidle")
        # 앱이 로딩될 때까지 타이틀 대기
        page.wait_for_selector("text=60/40은 아직 유효한가", timeout=60000)
        page.wait_for_timeout(2500)

        for name, preset, weights in SHOTS:
            # 새로고침해서 초기화 (상태 잔존 방지)
            page.reload(wait_until="networkidle")
            page.wait_for_selector("text=60/40은 아직 유효한가", timeout=60000)
            page.wait_for_timeout(1500)

            # 프리셋 선택 (radio) — input은 숨겨져 있으니 value 인덱스로 JS 클릭
            idx = PRESET_ORDER.index(preset)
            pg_radio = page.locator("[data-testid='stRadioGroup'] input[type=radio]").nth(idx)
            pg_radio.evaluate("el => el.click()")
            page.wait_for_timeout(800)

            # 슬라이더 설정
            for asset, w in weights.items():
                try:
                    set_slider(page, asset, w)
                except Exception as e:
                    print(f"  ! slider {asset} failed: {e}")
            page.wait_for_timeout(2500)  # 리렌더 대기

            path = OUT / f"{name}.png"
            page.screenshot(path=str(path), full_page=True)
            print("captured", path.name)

        browser.close()
    print("ALL DONE ->", OUT)


if __name__ == "__main__":
    main()
