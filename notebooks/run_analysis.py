"""analysis.ipynb의 셀 구성을 그대로 실행하는 스크립트 (실행 검증용)."""
# [셀1] 환경 준비 및 모듈 로드
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
warnings.filterwarnings("ignore")

from src.fetch_data import load
from src import metrics as M

FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
mpl.rcParams["figure.dpi"] = 120
mpl.rcParams["axes.unicode_minus"] = False
# 한글 폰트: macOS 'AppleGothic' / Windows 'Malgun Gothic' / Linux 'NanumGothic'
mpl.rcParams["font.family"] = "AppleGothic"

# [셀2] 데이터 로드 및 기간·컬럼·결측 확인
prices_raw, macro = load()
print(prices_raw.info())

summary = pd.DataFrame({
    "시작일": prices_raw.apply(lambda s: s.first_valid_index()),
    "종료일": prices_raw.apply(lambda s: s.last_valid_index()),
    "관측수": prices_raw.notna().sum(),
    "결측수": prices_raw.isna().sum(),
})
print(summary)

# [셀3] 거래일 정렬 + 창 A/B/C 분리
prices = M.align_to_market(prices_raw, "SPY")

WIN_A = ["SPY", "SHY", "TLT", "GLD"]
WIN_B = WIN_A + ["BTC-USD"]
WIN_C = WIN_A + ["IBIT"]

pA = prices[WIN_A].dropna()
pB = prices[WIN_B].dropna()
pC = prices[WIN_C].dropna()

rA, rB, rC = M.daily_returns(pA), M.daily_returns(pB), M.daily_returns(pC)
print({"A": len(rA), "B": len(rB), "C": len(rC)})

# 이상치: ±10% 초과 일간 수익률은 2008·2020의 실제 사건 → 제거하지 않는다
outliers = (rB.abs() > 0.10).sum()
print("outliers ±10%:", dict(outliers))

# [셀4] 금리·물가 정렬
dff = macro["DFF"].reindex(prices.index).ffill()
cpi_yoy = M.inflation_yoy(macro["CPIAUCSL"]).reindex(prices.index).ffill()
regime = M.rate_regime(dff)
print(regime.value_counts())

# [셀5] 기법 2~6: 롤링 상관 / 변동성 / 낙폭 / 조건부 통계 / 국면 집계
corr_A = M.rolling_corr(rA, "SPY", 252)
corr_B = M.rolling_corr(rB, "SPY", 252)
vol_B = M.rolling_vol(rB)
cum_B = M.cumulative(rB)
dd_B = M.drawdown(cum_B)

crash = M.crash_day_stats(rB, "SPY", 0.05)
regime_corr = corr_B.join(regime).groupby("regime").mean()
annual = (rB.groupby(rB.index.year).apply(lambda d: (1 + d).prod() - 1))

print("\n--- crash (Q3) ---")
print(crash.round(4))
print("\n--- regime_corr ---")
print(regime_corr.round(3))
print("\n--- annual (tail 6) ---")
print(annual.round(3).tail(6))

# [셀6] 5개 조합 성과 비교표 (Q5)
PORTS = {
    "클래식 60/40": {"SPY": .6, "TLT": .4},
    "단기채 60/40": {"SPY": .6, "SHY": .4},
    "금 추가":      {"SPY": .55, "TLT": .3, "GLD": .15},
    "5자산":        {"SPY": .5, "SHY": .15, "TLT": .15, "GLD": .15, "BTC-USD": .05},
    "100% 주식":    {"SPY": 1.0},
}
port_ret = pd.DataFrame({k: M.portfolio_returns(rB, w) for k, w in PORTS.items()})
table = pd.DataFrame({k: M.summarize(port_ret[k]) for k in port_ret}).T
table["2022년"] = port_ret.loc["2022"].add(1).prod() - 1
print("\n--- portfolio table ---")
print(table.round(4))

# [셀7] F1 정규화 누적수익 (BTC는 로그축 별도)
fig, ax = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                       gridspec_kw={"height_ratios": [2, 1]})
(cum_B[WIN_A] / cum_B[WIN_A].iloc[0] * 100).plot(ax=ax[0])
ax[0].set_title("4자산 정규화 누적수익 (시작=100)"); ax[0].set_ylabel("지수")
(cum_B["BTC-USD"] / cum_B["BTC-USD"].iloc[0] * 100).plot(ax=ax[1], color="orange", logy=True)
ax[1].set_title("비트코인 (로그축)")
fig.tight_layout(); fig.savefig(FIG / "F1_cumulative.png"); plt.close(fig)

# [셀8] F2 롤링 252일 상관계수
fig, ax = plt.subplots(figsize=(12, 5))
corr_B.plot(ax=ax, lw=1.2)
ax.axhline(0, color="black", lw=1)
ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2023-06-30"), color="red", alpha=.08)
ax.set_title("vs SPY 롤링 252일 상관계수 — 0선 위로 올라간 구간이 '분산 실패' 국면")
ax.set_ylabel("상관계수")
fig.tight_layout(); fig.savefig(FIG / "F2_rolling_corr.png"); plt.close(fig)

# [셀9] F3 상관계수 + 기준금리 이중축
fig, ax1 = plt.subplots(figsize=(12, 5))
corr_B["TLT"].plot(ax=ax1, color="navy", label="TLT-SPY 상관")
ax1.axhline(0, color="black", lw=.8); ax1.set_ylabel("상관계수", color="navy")
ax2 = ax1.twinx()
dff.plot(ax=ax2, color="crimson", alpha=.6, label="기준금리(DFF)")
ax2.set_ylabel("기준금리 %", color="crimson")
ax1.set_title("금리 인상 국면과 상관계수 반전의 시간적 일치")
fig.tight_layout(); fig.savefig(FIG / "F3_corr_rate.png"); plt.close(fig)

# [셀10] F4 연도×자산 수익률 히트맵
import seaborn as sns
fig, ax = plt.subplots(figsize=(8, 9))
sns.heatmap(annual * 100, annot=True, fmt=".1f", center=0,
            cmap="RdYlGn", cbar_kws={"label": "연간 수익률 %"}, ax=ax)
ax.set_title("자산 × 연도 수익률 — 2022년 행을 보라")
fig.tight_layout(); fig.savefig(FIG / "F4_heatmap.png"); plt.close(fig)

# [셀11] F5 주식 급락일 조건부 평균 수익률
fig, ax = plt.subplots(figsize=(9, 5))
crash[["전체 평균", crash.columns[1]]].mul(100).plot.bar(ax=ax)
ax.axhline(0, color="black", lw=.8); ax.set_ylabel("일간 평균 수익률 %")
ax.set_title("평상시 vs 주식 급락일(하위 5%) 자산별 평균 수익률")
fig.tight_layout(); fig.savefig(FIG / "F5_crash_days.png"); plt.close(fig)

# [셀12] F6 포트폴리오 누적수익 + 낙폭
cum_p = M.cumulative(port_ret)
fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                       gridspec_kw={"height_ratios": [2, 1]})
cum_p.plot(ax=ax[0], logy=True); ax[0].set_title("포트폴리오 누적수익(로그축)")
M.drawdown(cum_p).mul(100).plot(ax=ax[1]); ax[1].set_title("낙폭 %")
fig.tight_layout(); fig.savefig(FIG / "F6_portfolios.png"); plt.close(fig)

# [셀13] BTC-USD 현물 결과가 IBIT ETF로도 재현되는지 확인
print("\n--- 창 C 교차 검증 ---")
print("IBIT vs SPY corr:", rC.corr()["SPY"])
print("BTC-USD(동기) vs SPY corr:", rB.loc[rC.index].corr()["SPY"])

print("\nDONE")
