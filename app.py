import streamlit as st

from modules import benchmarks, depreciation, lcca, loans, project_worth, savings
from modules.common import CURRENCY_SYMBOLS

st.set_page_config(page_title="Engineering Economy & Financial Calculator", page_icon="💵", layout="wide")

st.title("💵 Engineering Economy & Financial Calculator")
st.markdown("Interactive tool for engineering economics, loans, vehicle buy-vs-lease analysis, investments and depreciation.")

# --- Sidebar -----------------------------------------------------------------
st.sidebar.header("1. Region & Currency")
country = st.sidebar.selectbox("Select Country", list(CURRENCY_SYMBOLS))
cur = CURRENCY_SYMBOLS[country]
if country == "Other / Custom":
    cur = st.sidebar.text_input("Currency symbol", value="$", max_chars=4) or "$"

st.sidebar.header("2. Calculator Selection")
MODULES = [
    "Loan / Mortgage / Auto",
    "Savings & Fixed Deposit Investment",
    "Depreciation Analysis (SL, DDB & MACRS)",
    "Project Evaluation (PW / FW / EUAW)",
    "Equipment Life-Cycle Cost (LCCA)",
    "Bank Rate Reference Table",
]
mode = st.sidebar.selectbox("Choose Calculator / Module", MODULES)

# --- Routing -----------------------------------------------------------------
if mode == MODULES[0]:
    st.sidebar.header("3. Loan Options")
    category = st.sidebar.selectbox("Loan Category", loans.CATEGORY_OPTIONS)
    loans.render(cur, category)
elif mode == MODULES[1]:
    savings.render(cur)
elif mode == MODULES[2]:
    depreciation.render(cur)
elif mode == MODULES[3]:
    project_worth.render(cur)
elif mode == MODULES[4]:
    lcca.render(cur)
else:
    benchmarks.render(country)

st.markdown("---")
st.markdown(f"**Active Workspace:** Country: `{country}` | Module: `{mode}`")
