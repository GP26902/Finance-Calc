import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import caption, error, fmt

METHODS = ["Straight-Line (SL)", "Double Declining Balance (DDB, switches to SL)", "MACRS (half-year convention)"]


def render(cur: str) -> None:
    st.header("🏭 Equipment Depreciation Calculator")
    st.markdown("Evaluate book-value depreciation with the classic engineering-economy methods, including US tax MACRS.")

    method = st.selectbox("Depreciation Method", METHODS)
    c1, c2 = st.columns(2)
    cost = c1.number_input(f"Initial Asset Cost ({cur})", min_value=0.0, value=50000.0, step=5000.0)

    if method == METHODS[2]:
        cls = c2.selectbox("MACRS Property Class (years)", sorted(calc.MACRS_HALF_YEAR), index=1,
                           help="e.g. 5-yr: computers, vehicles, some equipment; 7-yr: most manufacturing machinery and office furniture.")
        caption("MACRS ignores salvage value and uses IRS Pub. 946 Table A-1 percentages (half-year convention).")
        df = calc.macrs(cost, cls)
    else:
        salvage = c2.number_input(f"Estimated Salvage Value ({cur})", min_value=0.0, value=5000.0, step=1000.0)
        life = st.slider("Useful Life / Recovery Period (Years)", 3, 30, 5)
        if salvage >= cost:
            error("Salvage value must be lower than the initial cost.")
            return
        df = calc.straight_line(cost, salvage, life) if method == METHODS[0] else calc.declining_balance(cost, salvage, life)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Depreciation", fmt(cur, df["Depreciation"].sum()))
    m2.metric("Year-1 Depreciation", fmt(cur, df["Depreciation"].iloc[1]))
    m3.metric("Final Book Value", fmt(cur, df["Book Value"].iloc[-1]))

    st.plotly_chart(px.line(df, x="Year", y="Book Value", markers=True, title=f"Book Value ({method})",
                            labels={"Book Value": f"Book Value ({cur})"}))
    money = cur + "{:,.2f}"
    st.dataframe(df.style.format({c: money for c in df.columns if c != "Year"}), hide_index=True)
