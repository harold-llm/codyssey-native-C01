import sys
from pathlib import Path
import pandas as pd, streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))
from src.fetch_data import load
from src import metrics as M

st.set_page_config(page_title="60/40 재검증", layout="wide")
st.title("60/40은 아직 유효한가 — 자산 배분 탐색기")


@st.cache_data
def get_returns():
    prices, macro = load()
    prices = M.align_to_market(prices, "SPY")
    cols = ["SPY", "SHY", "TLT", "GLD", "BTC-USD"]
    return M.daily_returns(prices[cols].dropna()), macro


ret, macro = get_returns()

PRESETS = {
    "전체": (ret.index.min(), ret.index.max()),
    "2008 금융위기": ("2007-10-01", "2009-06-30"),
    "2020 코로나": ("2020-01-01", "2020-12-31"),
    "2022 인플레이션": ("2022-01-01", "2023-06-30"),
}

with st.sidebar:
    st.header("기간")
    preset = st.radio("프리셋", list(PRESETS), index=0)
    st.header("자산 비중 (%)")
    w = {c: st.slider(c, 0, 100, v) for c, v in
         zip(ret.columns, [60, 0, 40, 0, 0])}

start, end = PRESETS[preset]
sub = ret.loc[str(start):str(end)]
if sum(w.values()) == 0:
    st.warning("비중을 하나 이상 설정하세요."); st.stop()

mine = M.portfolio_returns(sub, w)
bench = M.portfolio_returns(sub, {"SPY": .6, "TLT": .4})
stats = M.summarize(mine)

c = st.columns(4)
c[0].metric("CAGR", f"{stats['CAGR']:.2%}")
c[1].metric("연율 변동성", f"{stats['Vol']:.2%}")
c[2].metric("최대낙폭", f"{stats['MaxDD']:.2%}")
c[3].metric("Sharpe(무위험 0 가정)", f"{stats['Sharpe']:.2f}")

st.subheader("누적수익 — 내 포트폴리오 vs 클래식 60/40")
st.line_chart(pd.DataFrame({"내 조합": M.cumulative(mine), "60/40": M.cumulative(bench)}))

st.subheader("vs SPY 롤링 252일 상관계수")
st.line_chart(M.rolling_corr(sub, "SPY", min(252, max(20, len(sub) // 3))))

st.caption("고정 비중 단순 가중(일별 리밸런싱 가정), 수정종가 기준, 세금·거래비용 미반영.")
