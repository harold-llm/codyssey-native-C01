"""가격(yfinance) + 거시지표(FRED) 수집 및 CSV 캐시.

사용법:
    python src/fetch_data.py            # 캐시가 없을 때만 다운로드
    python src/fetch_data.py --refresh  # 강제 재다운로드
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

START = "2004-11-18"          # GLD 상장일 = 창 A 시작
PRICE_TICKERS = ["SPY", "SHY", "TLT", "GLD", "BTC-USD", "IBIT"]
FRED_SERIES = ["DFF", "CPIAUCSL", "T10Y2Y"]

PRICE_CSV = DATA / "prices.csv"
MACRO_CSV = DATA / "macro.csv"


def fetch_prices(tickers=PRICE_TICKERS, start=START) -> pd.DataFrame:
    """수정종가(auto_adjust=True) 기준 일별 가격.

    분배금 재투자를 반영하지 않으면 SHY/TLT 수익이 크게 과소평가된다.
    """
    raw = yf.download(tickers, start=start, auto_adjust=True,
                      progress=False, group_by="column")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    close = close.reindex(columns=tickers)
    close.index.name = "date"
    return close.sort_index()


def fetch_fred(series_id: str, start=START) -> pd.Series:
    """FRED CSV 직접 다운로드 — API 키 불필요."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["date", series_id]          # 컬럼명(DATE/observation_date) 변경 대응
    df["date"] = pd.to_datetime(df["date"])
    s = pd.to_numeric(df.set_index("date")[series_id], errors="coerce")  # '.' → NaN
    return s.loc[start:]


def fetch_macro(series=FRED_SERIES) -> pd.DataFrame:
    return pd.concat({sid: fetch_fred(sid) for sid in series}, axis=1).sort_index()


def load(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """캐시가 있으면 읽고, 없거나 refresh면 받아서 저장."""
    if refresh or not PRICE_CSV.exists():
        fetch_prices().to_csv(PRICE_CSV)
    if refresh or not MACRO_CSV.exists():
        fetch_macro().to_csv(MACRO_CSV)
    prices = pd.read_csv(PRICE_CSV, index_col=0, parse_dates=True)
    macro = pd.read_csv(MACRO_CSV, index_col=0, parse_dates=True)
    return prices, macro


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--refresh", action="store_true")
    args = p.parse_args()
    prices, macro = load(refresh=args.refresh)
    print("prices", prices.shape, prices.index.min().date(), "→", prices.index.max().date())
    print(prices.notna().sum())
    print("macro ", macro.shape)
