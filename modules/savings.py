import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import fmt


def render(cur: str) -> None:
    st.header("📈 Savings & Fixed Deposit Investment Calculator")
    st.markdown("Calculate compound growth. Choose whether the quoted rate is a nominal rate or an APY.")

    c1, c2 = st.columns(2)
    with c1:
        principal = st.number_input(f"Initial Principal ({cur})", min_value=0.0, value=10000.0, step=1000.0)
        years = st.slider("Investment Horizon (Years)", 1, 30, 5)
    with c2:
        rate = st.number_input("Quoted Annual Rate (%)", min_value=0.0, max_value=50.0, value=4.5, step=0.1)
        rate_type = st.radio("Rate type", ["Nominal annual rate (APR)", "APY (effective annual yield)"], horizontal=True)
        freq = st.selectbox("Compounding Frequency", ["Monthly", "Annually", "Daily"])

    is_apy = rate_type.startswith("APY")
    n = {"Monthly": 12, "Annually": 1, "Daily": 365}[freq]
    if is_apy:
        st.caption("An APY already includes the effect of compounding, so the frequency does not change the result.")

    fv = calc.future_value(principal, rate, n, years, is_apy)
    apy = rate if is_apy else calc.effective_annual_yield(rate, n)
    m1, m2, m3 = st.columns(3)
    m1.metric("Projected Future Value", fmt(cur, fv))
    m2.metric("Total Interest Earned", fmt(cur, fv - principal))
    m3.metric("Effective Annual Yield", f"{apy:.3f}%")

    df = pd.DataFrame({"Year": range(0, years + 1),
                       "Portfolio Value": [calc.future_value(principal, rate, n, y, is_apy) for y in range(0, years + 1)]})
    st.plotly_chart(px.bar(df, x="Year", y="Portfolio Value", text_auto=".2s", title="Investment Growth Over Time",
                           labels={"Portfolio Value": f"Total Value ({cur})"}))
