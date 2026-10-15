import pandas as pd
import plotly.express as px
import streamlit as st

from modules.common import info, warning

# Static, illustrative snapshot - NOT live data. Update before relying on it.
BANK_BENCHMARKS = {
    "United States (USA)": [
        {"Bank Name": "Chase Bank", "Type": "Private", "Mortgage Rate (%)": 6.80, "Savings APY (%)": 0.01, "CD Rate (%)": 4.25},
        {"Bank Name": "Bank of America", "Type": "Private", "Mortgage Rate (%)": 6.90, "Savings APY (%)": 0.02, "CD Rate (%)": 4.00},
        {"Bank Name": "Wells Fargo", "Type": "Private", "Mortgage Rate (%)": 6.85, "Savings APY (%)": 0.015, "CD Rate (%)": 4.10},
        {"Bank Name": "Capital One", "Type": "Private", "Mortgage Rate (%)": 6.70, "Savings APY (%)": 3.50, "CD Rate (%)": 4.40},
        {"Bank Name": "Ally Bank (Digital)", "Type": "Private", "Mortgage Rate (%)": 6.65, "Savings APY (%)": 4.00, "CD Rate (%)": 4.50},
    ],
    "India": [
        {"Bank Name": "State Bank of India (SBI)", "Type": "Public", "Mortgage Rate (%)": 8.50, "Savings APY (%)": 2.70, "CD Rate (%)": 6.50},
        {"Bank Name": "HDFC Bank", "Type": "Private", "Mortgage Rate (%)": 8.70, "Savings APY (%)": 3.00, "CD Rate (%)": 6.75},
        {"Bank Name": "ICICI Bank", "Type": "Private", "Mortgage Rate (%)": 8.75, "Savings APY (%)": 3.00, "CD Rate (%)": 6.70},
        {"Bank Name": "Axis Bank", "Type": "Private", "Mortgage Rate (%)": 8.80, "Savings APY (%)": 3.00, "CD Rate (%)": 6.60},
    ],
}


def render(country: str) -> None:
    st.header("📊 Bank Rate Reference Table")
    st.markdown(f"Illustrative institution rates for `{country}`.")
    warning("Static illustrative snapshot, **not live data**. Verify current rates with each institution before relying on them.")

    if country not in BANK_BENCHMARKS:
        info(f"No reference rates are stored for {country} yet. Enter your lender's rates directly in the loan and savings calculators.")
        return
    df = pd.DataFrame(BANK_BENCHMARKS[country])
    st.dataframe(df, hide_index=True)
    st.plotly_chart(px.bar(df, x="Bank Name", y=["Mortgage Rate (%)", "CD Rate (%)", "Savings APY (%)"], barmode="group",
                           title=f"Rate Comparison Across Institutions in {country}", labels={"value": "Rate (%)", "variable": ""}))
