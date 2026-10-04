import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Page Configuration
st.set_page_config(
    page_title="Global Engineering Economy & Financial Calculator",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Global Engineering Economy & Financial Calculator")
st.markdown("An advanced interactive tool modeling engineering economics, loans, investments, depreciation, and custom bank offers.")

# --- SIDEBAR: COMPREHENSIVE NAVIGATION ---
st.sidebar.header("1. Geographic Region")
country = st.sidebar.selectbox(
    "Select Country", 
    ["United States (USA)", "India", "Canada", "United Kingdom", "Other / Custom"]
)

st.sidebar.header("2. Calculator Selection")
calculator_mode = st.sidebar.selectbox(
    "Choose Calculator / Module",
    [
        "Loan / Mortgage Amortization", 
        "Savings & Fixed Deposit Investment", 
        "Depreciation Analysis (Straight-Line & MACRS)", 
        "Present Worth / Future Worth (Equivalent Uniform Annual Worth)",
        "Bank Benchmark Rate Comparison"
    ]
)

# Conditional Sidebar Option for Loans
loan_category = "Home Mortgage"
if calculator_mode == "Loan / Mortgage Amortization":
    st.sidebar.header("3. Loan Options")
    loan_category = st.sidebar.selectbox("Loan Category", ["Home Mortgage", "Auto / Vehicle Loan", "Personal Loan"])

# --- BANK BENCHMARK DICTIONARY ---
bank_benchmarks = {
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
    ]
}

# ==========================================
# MODULE 1: LOAN / MORTGAGE AMORTIZATION
# ==========================================
if calculator_mode == "Loan / Mortgage Amortization":
    st.header(f"🏡 {loan_category} Amortization Calculator")
    st.markdown("Model monthly installments, down payments, total interest accrued, and generate complete amortization schedules.")
    
    col1, col2 = st.columns(2)
    with col1:
        asset_price = st.number_input("Total Asset / Purchase Price ($)", value=350000, step=10000)
        down_payment = st.number_input(
            "Out-of-Pocket Down Payment ($)", 
            value=70000, 
            step=5000,
            help="💡 Recommended: A 10% to 30% down payment reduces your financed principal and lowers monthly payments."
        )
        years = st.slider("Loan Term (Years)", min_value=1, max_value=30, value=30)
    with col2:
        custom_rate = st.number_input(
            "Annual Interest Rate (%) [APR]", 
            value=6.5, 
            step=0.1,
            help="Enter the rate provided by your bank or financial representative."
        )
        hidden_fees = st.number_input("Estimated Hidden Fees / Processing Charges ($)", value=1000.0, step=250.0)

    # Calculate actual loan principal after down payment
    loan_amount = max(0.0, asset_price - down_payment)
    down_payment_pct = (down_payment / asset_price * 100) if asset_price > 0 else 0.0
    
    st.info(f"💼 **Financing Breakdown:** Asset Price: `${asset_price:,.2f}` | Down Payment: `${down_payment:,.2f}` (`{down_payment_pct:.1f}%`) | **Principal Financed:** `${loan_amount:,.2f}`")

    # Formulas
    monthly_interest_rate = (custom_rate / 100) / 12
    total_payments = years * 12
    
    if monthly_interest_rate > 0:
        monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**total_payments) / ((1 + monthly_interest_rate)**total_payments - 1)
    else:
        monthly_payment = loan_amount / total_payments
        
    total_paid_installments = monthly_payment * total_payments
    total_paid = total_paid_installments + down_payment + hidden_fees
    total_interest = total_paid_installments - loan_amount

    # Metrics Display
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Estimated Monthly Payment", f"${monthly_payment:,.2f}")
    m2.metric("Total Interest Paid", f"${total_interest:,.2f}")
    m3.metric("Hidden Fees", f"${hidden_fees:,.2f}")
    m4.metric("Total Cost of Loan", f"${total_paid:,.2f}")

    # Amortization Schedule Data
    schedule = []
    remaining_balance = loan_amount
    for month in range(1, total_payments + 1):
        interest_payment = remaining_balance * monthly_interest_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        schedule.append({
            "Month": month,
            "Remaining Balance": max(0, remaining_balance),
            "Principal Paid": principal_payment,
            "Interest Paid": interest_payment,
            "Total Monthly Payment": monthly_payment
        })
    
    df_schedule = pd.DataFrame(schedule)
    fig = px.line(df_schedule, x="Month", y="Remaining Balance", title=f"{loan_category} Balance Reduction Over {years} Years",
                  labels={"Remaining Balance": "Remaining Balance ($)", "Month": "Months"})
    st.plotly_chart(fig, use_container_width=True)

    # Amortization Table & CSV Export
    st.subheader("📋 Month-by-Month Amortization Schedule")
    st.dataframe(df_schedule.style.format({
        "Remaining Balance": "${:,.2f}",
        "Principal Paid": "${:,.2f}",
        "Interest Paid": "${:,.2f}",
        "Total Monthly Payment": "${:,.2f}"
    }), use_container_width=True)

    csv_data = df_schedule.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Amortization Schedule to CSV (Excel Compatible)",
        data=csv_data,
        file_name=f"{loan_category.lower().replace(' ', '_')}_amortization_schedule.csv",
        mime="text/csv"
    )

# ==========================================
# MODULE 2: SAVINGS & FIXED DEPOSIT
# ==========================================
elif calculator_mode == "Savings & Fixed Deposit Investment":
    st.header("📈 Savings & Fixed Deposit Investment Calculator")
    st.markdown("Calculate compound growth and investment returns over time.")
    
    col1, col2 = st.columns(2)
    with col1:
        initial_deposit = st.number_input("Initial Principal Investment ($)", value=10000, step=1000)
        investment_years = st.slider("Investment Horizon (Years)", min_value=1, max_value=20, value=5)
    with col2:
        custom_deposit_rate = st.number_input("Annual Interest Rate / Yield (%) [APY]", value=4.5, step=0.1)
        compounding_freq = st.selectbox("Compounding Frequency", ["Monthly", "Annually", "Daily"])

    n = 12 if compounding_freq == "Monthly" else (365 if compounding_freq == "Daily" else 1)
    future_value = initial_deposit * ((1 + (custom_deposit_rate / 100) / n) ** (n * investment_years))
    total_earnings = future_value - initial_deposit

    m1, m2 = st.columns(2)
    m1.metric("Projected Future Value", f"${future_value:,.2f}")
    m2.metric("Total Interest Earned", f"${total_earnings:,.2f}")

    years_list = list(range(0, investment_years + 1))
    growth_data = [initial_deposit * ((1 + (custom_deposit_rate / 100) / n) ** (n * yr)) for yr in years_list]
    df_growth = pd.DataFrame({"Year": years_list, "Portfolio Value": growth_data})

    fig_growth = px.bar(df_growth, x="Year", y="Portfolio Value", title="Investment Growth Over Time",
                        text_auto='.2s', labels={"Portfolio Value": "Total Value ($)"})
    st.plotly_chart(fig_growth, use_container_width=True)

# ==========================================
# MODULE 3: DEPRECIATION ANALYSIS
# ==========================================
elif calculator_mode == "Depreciation Analysis (Straight-Line & MACRS)":
    st.header("🏭 Engineering Equipment Depreciation Calculator")
    st.markdown("Evaluate asset book value depreciation using classic engineering economy methods.")
    
    col1, col2 = st.columns(2)
    with col1:
        asset_cost = st.number_input("Initial Asset Cost ($)", value=50000, step=5000)
        salvage_value = st.number_input("Estimated Salvage Value ($)", value=5000, step=1000)
        dep_years = st.slider("Recovery Period (Years)", min_value=3, max_value=15, value=5)
    with col2:
        dep_method = st.selectbox("Depreciation Method", ["Straight-Line (SL)", "Double Declining Balance (DDB)"])

    dep_schedule = []
    book_value = asset_cost
    
    if dep_method == "Straight-Line (SL)":
        annual_dep = (asset_cost - salvage_value) / dep_years
        for yr in range(1, dep_years + 1):
            book_value = max(salvage_value, book_value - annual_dep)
            dep_schedule.append({"Year": yr, "Book Value": book_value, "Annual Depreciation": annual_dep})
    else:
        rate = 2 / dep_years
        for yr in range(1, dep_years + 1):
            annual_dep = book_value * rate
            book_value = max(salvage_value, book_value - annual_dep)
            dep_schedule.append({"Year": yr, "Book Value": book_value, "Annual Depreciation": annual_dep})

    df_dep = pd.DataFrame(dep_schedule)
    m1, m2 = st.columns(2)
    m1.metric("Final Book Value", f"${df_dep['Book Value'].iloc[-1]:,.2f}")
    m2.metric("Depreciation Method Selected", dep_method)

    fig_dep = px.line(df_dep, x="Year", y="Book Value", title=f"Asset Depreciation Schedule ({dep_method})", markers=True)
    st.plotly_chart(fig_dep, use_container_width=True)

# ==========================================
# MODULE 4: PRESENT WORTH / FUTURE WORTH
# ==========================================
elif calculator_mode == "Present Worth / Future Worth (Equivalent Uniform Annual Worth)":
    st.header("⚖️ Engineering Project Present Worth & EUAW Comparison")
    st.markdown("Compare capital investments, cash flows, and equivalent uniform annual worth (EUAW).")

    col1, col2 = st.columns(2)
    with col1:
        initial_investment = st.number_input("Initial Capital Investment ($)", value=100000, step=10000)
        annual_revenue = st.number_input("Net Annual Operating Revenue ($)", value=25000, step=2000)
    with col2:
        project_life = st.slider("Project Useful Life (Years)", min_value=1, max_value=25, value=10)
        interest_rate_pw = st.number_input("Minimum Attractive Rate of Return - MARR (%)", value=8.0, step=0.5)

    i = interest_rate_pw / 100
    if i > 0:
        pw_revenue = annual_revenue * (((1 + i)**project_life - 1) / (i * (1 + i)**project_life))
    else:
        pw_revenue = annual_revenue * project_life
        
    net_present_worth = pw_revenue - initial_investment
    eauw = net_present_worth * ((i * (1 + i)**project_life) / ((1 + i)**project_life - 1)) if i > 0 else net_present_worth / project_life

    m1, m2 = st.columns(2)
    m1.metric("Net Present Worth (NPW)", f"${net_present_worth:,.2f}")
    m2.metric("Equivalent Uniform Annual Worth (EUAW)", f"${eauw:,.2f}")

    cf_years = list(range(0, project_life + 1))
    cf_values = [-initial_investment] + [annual_revenue] * project_life
    df_cf = pd.DataFrame({"Year": cf_years, "Net Cash Flow": cf_values})
    
    fig_cf = px.bar(df_cf, x="Year", y="Net Cash Flow", title="Project Cash Flow Diagram", text_auto='.2s')
    st.plotly_chart(fig_cf, use_container_width=True)

# ==========================================
# MODULE 5: BANK BENCHMARK COMPARISON
# ==========================================
else:
    st.header("📊 National Bank Benchmark Rate Comparison")
    st.markdown(f"Review live public and private institution benchmarks for `{country}`.")
    
    if country in bank_benchmarks:
        df_banks = pd.DataFrame(bank_benchmarks[country])
        st.dataframe(df_banks, use_container_width=True, hide_index=True)
        
        fig_bank = px.bar(df_banks, x="Bank Name", y=["Mortgage Rate (%)", "CD Rate (%)"], barmode="group",
                          title=f"Interest Rate Comparison Across Banks in {country}")
        st.plotly_chart(fig_bank, use_container_width=True)
    else:
        st.info("Custom country selected. Input your local bank rates directly inside the individual calculators.")

st.markdown("---")
st.markdown(f"**Active Workspace:** Country: `{country}` | Module: `{calculator_mode}`")