import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import fmt, info, success, warning


def render(cur: str) -> None:
    st.header("⚖️ Project Evaluation: Present Worth, Future Worth & EUAW")
    st.markdown("Evaluate a capital investment against your Minimum Attractive Rate of Return (MARR).")

    c1, c2 = st.columns(2)
    with c1:
        initial = st.number_input(f"Initial Capital Investment ({cur})", min_value=0.0, value=100000.0, step=10000.0)
        annual = st.number_input(f"Net Annual Benefit ({cur})", value=25000.0, step=2000.0)
        salvage = st.number_input(f"Salvage Value at End of Life ({cur})", min_value=0.0, value=0.0, step=5000.0)
    with c2:
        life = st.slider("Project Useful Life (Years)", 1, 40, 10)
        marr = st.number_input("Minimum Attractive Rate of Return, MARR (%)", min_value=0.0, max_value=100.0, value=8.0, step=0.5)

    npw, euaw, fw = calc.project_worth(initial, annual, life, marr, salvage)
    m1, m2, m3 = st.columns(3)
    m1.metric("Net Present Worth (NPW)", fmt(cur, npw))
    m2.metric("Equivalent Uniform Annual Worth (EUAW)", fmt(cur, euaw))
    m3.metric("Future Worth (FW)", fmt(cur, fw))

    if npw > 0:
        success("NPW > 0: the project earns more than the MARR and is economically acceptable.")
    elif npw < 0:
        warning("NPW < 0: the project does not earn the MARR at these assumptions.")
    else:
        info("NPW = 0: the project earns exactly the MARR.")

    flows = [-initial] + [annual] * life
    flows[-1] += salvage
    df = pd.DataFrame({"Year": range(0, life + 1), "Net Cash Flow": flows})
    st.plotly_chart(px.bar(df, x="Year", y="Net Cash Flow", text_auto=".2s", title="Project Cash Flow Diagram",
                           labels={"Net Cash Flow": f"Net Cash Flow ({cur})"}))
