"""수익률·상관·변동성·낙폭·포트폴리오·국면 계산 함수 모음."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def align_to_market(prices: pd.DataFrame, calendar_col: str = "SPY") -> pd.DataFrame:
    """SPY 거래일을 마스터 캘린더로 삼아 정렬.

    BTC-USD는 주말에도 거래되므로 정렬하지 않으면 상관계수가 왜곡된다.
    """
    cal = prices[calendar_col].dropna().index
    return prices.reindex(cal).ffill()


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """가격이 아니라 수익률로 상관을 내야 추세로 인한 가짜 상관을 피한다."""
    return prices.pct_change().dropna(how="all")


def rolling_corr(returns: pd.DataFrame, base: str = "SPY", window: int = TRADING_DAYS) -> pd.DataFrame:
    others = [c for c in returns.columns if c != base]
    return pd.DataFrame(
        {c: returns[c].rolling(window).corr(returns[base]) for c in others}
    )


def rolling_vol(returns: pd.DataFrame, window: int = TRADING_DAYS) -> pd.DataFrame:
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS)


def drawdown(cum: pd.Series | pd.DataFrame):
    """전고점 대비 하락률."""
    return cum / cum.cummax() - 1


def cumulative(returns: pd.Series | pd.DataFrame):
    return (1 + returns.fillna(0)).cumprod()


def cagr(returns: pd.Series) -> float:
    cum = (1 + returns.fillna(0)).prod()
    years = len(returns) / TRADING_DAYS
    return cum ** (1 / years) - 1 if years > 0 else np.nan


def summarize(returns: pd.Series) -> dict:
    cum = cumulative(returns)
    return {
        "CAGR": cagr(returns),
        "Vol": returns.std() * np.sqrt(TRADING_DAYS),
        "MaxDD": drawdown(cum).min(),
        "Sharpe": cagr(returns) / (returns.std() * np.sqrt(TRADING_DAYS)),
    }


def portfolio_returns(returns: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """고정 비중 단순 가중(일별 리밸런싱 가정). 한계점에 명시할 것."""
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()
    cols = list(w.index)
    return (returns[cols].fillna(0) * w).sum(axis=1)


def crash_day_stats(returns: pd.DataFrame, base: str = "SPY", q: float = 0.05) -> pd.DataFrame:
    """⭐ 조건부 통계: SPY 하위 q 분위 날짜의 타 자산 평균 수익률.

    '평균적으로는 무상관이지만 정작 필요할 때 같이 빠지는' 자산을 색출한다.
    """
    thr = returns[base].quantile(q)
    crash = returns[returns[base] <= thr]
    return pd.DataFrame({
        "전체 평균": returns.mean(),
        f"급락일 평균(하위 {int(q*100)}%)": crash.mean(),
        "급락일 승률": (crash > 0).mean(),
    })


def rate_regime(dff: pd.Series, lookback: int = 63, thr: float = 0.25) -> pd.Series:
    """기준금리 3개월(63거래일) 변화량으로 인상/동결/인하 국면 분류."""
    chg = dff.ffill().diff(lookback)
    return pd.Series(
        np.where(chg > thr, "인상", np.where(chg < -thr, "인하", "동결")),
        index=dff.index, name="regime",
    )


def inflation_yoy(cpi: pd.Series) -> pd.Series:
    """월별 CPI → 전년비(%). 일별 정렬은 ffill (미래 보간 금지: look-ahead 방지)."""
    monthly = cpi.dropna().resample("MS").last()
    return (monthly.pct_change(12) * 100).rename("CPI_YoY")
