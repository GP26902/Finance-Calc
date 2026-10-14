"""Loan screens: Home Mortgage, Auto Loan, Personal Loan, and Auto Buy-vs-Lease."""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import fmt

LOAN_CATEGORIES = {
    "Home Mortgage": {
        "icon": "🏡", "price_label": "Home Purchase Price", "price": 350000.0, "price_step": 10000.0,
        "down": 70000.0, "down_step": 5000.0, "max_years": 30, "years": 30, "rate": 6.5,
        "tip": "A 10-30% down payment reduces the financed principal and the monthly payment.",
    },
    "Auto / Vehicle Loan": {
        "icon": "🚗", "price_label": "Vehicle Price", "price": 35000.0, "price_step": 1000.0,
        "down": 5000.0, "down_step": 500.0, "max_years": 8, "years": 5, "rate": 7.0,
        "tip": "Shorter auto terms cost less interest and reduce the risk of owing more than the vehicle is worth.",
    },
    "Personal Loan": {
        "icon": "💳", "price_label": "Loan Amount", "price": 15000.0, "price_step": 1000.0,
        "down": 0.0, "down_step": 500.0, "max_years": 10, "years": 3, "rate": 11.0,
        "tip": "Unsecured loans usually carry higher rates; leave the down payment at 0 if not applicable.",
    },
}
BUY_VS_LEASE = "Auto: Buy vs Lease"
CATEGORY_OPTIONS = ["Home Mortgage", "Auto / Vehicle Loan", BUY_VS_LEASE, "Personal Loan"]


def render(cur: str, category: str) -> None:
    if category == BUY_VS_LEASE:
        render_buy_vs_lease(cur)
    else:
        render_amortization(cur, category)


# ------------------------------------------------------------------ amortization
def render_amortization(cur: str, category: str) -> None:
    cfg = LOAN_CATEGORIES[category]
    k = category.replace(" ", "_").replace("/", "")
    st.header(f"{cfg['icon']} {category} Amortization Calculator")
    st.markdown("Model the monthly installment, total interest, true cost of borrowing (including fees), and the full amortization schedule.")

    c1, c2 = st.columns(2)
    with c1:
        price = st.number_input(f"{cfg['price_label']} ({cur})", min_value=0.0, value=cfg["price"],
                                step=cfg["price_step"], key=f"{k}_price")
        down = st.number_input(f"Down Payment ({cur})", min_value=0.0, value=cfg["down"],
                               step=cfg["down_step"], key=f"{k}_down", help=cfg["tip"])
        years = st.slider("Loan Term (Years)", 1, cfg["max_years"], cfg["years"], key=f"{k}_years")
    with c2:
        rate = st.number_input("Annual Interest Rate (%) [APR]", min_value=0.0, max_value=40.0,
                               value=cfg["rate"], step=0.1, key=f"{k}_rate",
                               help="Nominal annual rate quoted by the lender, compounded monthly.")
        fees = st.number_input(f"Origination / Closing Fees, paid upfront ({cur})", min_value=0.0,
                               value=1000.0, step=250.0, key=f"{k}_fees")

    if price <= 0:
        st.warning("Enter a price / loan amount greater than zero.")
        return
    if down > price:
        st.error("Down payment cannot exceed the purchase price.")
        return

    s = calc.loan_summary(price, down, rate, years, fees)
    st.info(f"**Financing breakdown:** Price `{fmt(cur, price)}` | Down payment `{fmt(cur, down)}` "
            f"(`{s['down_pct']:.1f}%`) | **Principal financed:** `{fmt(cur, s['principal'])}`")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Monthly Payment", fmt(cur, s["monthly_payment"]))
    m2.metric("Total Interest", fmt(cur, s["total_interest"]))
    m3.metric("Fees", fmt(cur, fees))
    m4.metric("Total Cost of Ownership", fmt(cur, s["total_cost"]))
    eff = s["effective_apr"]
    m5.metric("Effective APR incl. fees", f"{eff:.2f}%" if eff is not None else "n/a",
              help="The rate you actually pay once upfront fees are treated as reducing the cash you receive.")

    if s["principal"] == 0:
        st.success("Nothing is financed at this down payment.")
        return

    df = calc.amortization_schedule(s["principal"], rate, s["n_months"])
    start = pd.DataFrame([{"Month": 0, "Remaining Balance": s["principal"]}])
    fig = px.line(pd.concat([start, df[["Month", "Remaining Balance"]]]), x="Month", y="Remaining Balance",
                  title=f"{category}: Balance Reduction Over {years} Years",
                  labels={"Remaining Balance": f"Remaining Balance ({cur})"})
    st.plotly_chart(fig)

    annual = (df.assign(Year=(df["Month"] - 1) // 12 + 1)
                .groupby("Year")[["Principal Paid", "Interest Paid"]].sum().reset_index())
    st.plotly_chart(px.bar(annual, x="Year", y=["Principal Paid", "Interest Paid"], barmode="stack",
                           title="Where Each Year's Payments Go", labels={"value": f"Paid ({cur})", "variable": ""}))

    st.subheader("📋 Month-by-Month Amortization Schedule")
    money = cur + "{:,.2f}"
    st.dataframe(df.style.format({c: money for c in df.columns if c != "Month"}), hide_index=True)
    st.download_button("📥 Export Amortization Schedule (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name=f"{k.lower()}_amortization_schedule.csv", mime="text/csv")


# ------------------------------------------------------------------ buy vs lease
def render_buy_vs_lease(cur: str) -> None:
    st.header("🚗 Auto: Buy vs Lease")
    st.markdown("Compares financing and later selling the vehicle against leasing it over the **same time horizon**, "
                "on both a nominal basis and a **present-worth basis** (cash flows at different times are discounted "
                "at your opportunity cost of money, the engineering-economics way to compare alternatives).")

    with st.expander("Vehicle & purchase", expanded=True):
        a, b = st.columns(2)
        price = a.number_input(f"Negotiated Vehicle Price ({cur})", min_value=0.0, value=35000.0, step=1000.0, key="bvl_price")
        down = a.number_input(f"Cash Down Payment / Cap-Cost Reduction ({cur})", min_value=0.0, value=3000.0, step=500.0, key="bvl_down")
        tax = b.number_input("Sales Tax Rate (%)", min_value=0.0, max_value=20.0, value=6.25, step=0.25, key="bvl_tax",
                             help="Applied to the price when buying and to the monthly payment when leasing. Adjust for your state.")
        horizon = b.selectbox("Comparison Horizon = Lease Term (months)", [24, 36, 48], index=1, key="bvl_horizon")

    with st.expander("Buy (finance) assumptions", expanded=True):
        a, b = st.columns(2)
        loan_apr = a.number_input("Loan APR (%)", min_value=0.0, max_value=30.0, value=7.0, step=0.1, key="bvl_apr")
        loan_years = a.slider("Loan Term (Years)", 3, 8, 5, key="bvl_years")
        resale_pct = b.number_input("Expected Resale Value at End of Horizon (% of price)", min_value=0.0, max_value=100.0,
                                    value=55.0, step=1.0, key="bvl_resale",
                                    help="Depends on make, model and mileage; test it in the sensitivity table below.")
        buy_fees = b.number_input(f"Title / Documentation Fees ({cur})", min_value=0.0, value=500.0, step=50.0, key="bvl_buyfees")

    with st.expander("Lease assumptions", expanded=True):
        a, b = st.columns(2)
        lease_apr = a.number_input("Lease Rate, APR-equivalent (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.1, key="bvl_lapr",
                                   help="Money factor x 2400. Ask the dealer for the money factor and convert it.")
        residual_pct = a.number_input("Residual Value (% of vehicle price)", min_value=0.0, max_value=100.0, value=60.0, step=1.0,
                                      key="bvl_resid", help="Normally quoted as % of MSRP; price is used here as a proxy.")
        acq = b.number_input(f"Acquisition Fee ({cur})", min_value=0.0, value=695.0, step=25.0, key="bvl_acq")
        disp = b.number_input(f"Disposition Fee at Lease End ({cur})", min_value=0.0, value=395.0, step=25.0, key="bvl_disp")

    with st.expander("Usage & money assumptions", expanded=True):
        a, b = st.columns(2)
        allowed = a.number_input("Miles Allowed per Year", min_value=0.0, value=12000.0, step=1000.0, key="bvl_allowed")
        expected = a.number_input("Miles You Expect to Drive per Year", min_value=0.0, value=13000.0, step=1000.0, key="bvl_expected")
        over = b.number_input(f"Overage Charge per Mile ({cur})", min_value=0.0, value=0.25, step=0.05, key="bvl_over")
        opp = b.number_input("Opportunity Cost of Cash (% per year)", min_value=0.0, max_value=30.0, value=4.0, step=0.5, key="bvl_opp",
                             help="What your cash could otherwise earn (savings/CD yield) - used as the discount rate for present worth.")

    residual = price * residual_pct / 100
    if price <= 0 or down >= price:
        st.error("Enter a vehicle price greater than the down payment.")
        return
    if residual >= price - down:
        st.error("Residual value must be below the capitalized cost (price minus down payment).")
        return

    def buy_cost(resale_percent: float) -> dict:
        return calc.buy_total_cost(price, down, loan_apr, loan_years, horizon, price * resale_percent / 100, tax, buy_fees, opp)

    buy = buy_cost(resale_pct)
    lease = calc.lease_total_cost(price, down, residual, horizon, lease_apr, tax, acq, disp, allowed, expected, over, opp)

    diff = lease["present_worth_cost"] - buy["present_worth_cost"]
    if abs(diff) < 1:
        st.info("On a present-worth basis the two options are essentially equal.")
    elif diff > 0:
        st.success(f"**Buying is cheaper by {fmt(cur, diff)}** (present worth) over {horizon} months, "
                   f"about {fmt(cur, diff / horizon)} per month.")
    else:
        st.success(f"**Leasing is cheaper by {fmt(cur, -diff)}** (present worth) over {horizon} months, "
                   f"about {fmt(cur, -diff / horizon)} per month.")

    c1, c2 = st.columns(2)
    c1.metric("Buy: Monthly Payment", fmt(cur, buy["monthly_payment"]))
    c2.metric("Lease: Monthly Payment (incl. tax)", fmt(cur, lease["payment"]))
    st.caption(f"Lease money factor = {lease['money_factor']:.5f} | monthly depreciation {fmt(cur, lease['depreciation'])} "
               f"+ finance charge {fmt(cur, lease['finance_charge'])} + tax {fmt(cur, lease['tax'])} | "
               f"loan balance at end of horizon {fmt(cur, buy['balance_at_end'])}")

    rows = [
        ("Cash due at signing / purchase", buy["upfront"], lease["upfront"]),
        ("Monthly payment", buy["monthly_payment"], lease["payment"]),
        ("Payments made over horizon", buy["monthly_payment"] * buy["pay_months"], lease["payment"] * horizon),
        ("End of term: charges (+) / equity returned (-)", -buy["equity"], lease["end_charges"]),
        ("Net cost (nominal)", buy["nominal_cost"], lease["nominal_cost"]),
        ("Net cost (present worth)", buy["present_worth_cost"], lease["present_worth_cost"]),
        ("Equivalent monthly cost", buy["monthly_equivalent"], lease["monthly_equivalent"]),
    ]
    st.dataframe(pd.DataFrame({"Item": [r[0] for r in rows],
                               "Buy": [fmt(cur, r[1]) for r in rows],
                               "Lease": [fmt(cur, r[2]) for r in rows]}), hide_index=True)

    chart = pd.DataFrame({
        "Option": ["Buy", "Buy", "Lease", "Lease"],
        "Basis": ["Nominal", "Present worth", "Nominal", "Present worth"],
        f"Net Cost ({cur})": [buy["nominal_cost"], buy["present_worth_cost"],
                              lease["nominal_cost"], lease["present_worth_cost"]],
    })
    st.plotly_chart(px.bar(chart, x="Basis", y=f"Net Cost ({cur})", color="Option", barmode="group",
                           title=f"Net Cost of Each Option Over {horizon} Months"))

    st.subheader("Sensitivity to resale value")
    sens = []
    for delta in (-10, -5, 0, 5, 10):
        pct = min(100.0, max(0.0, resale_pct + delta))
        pw = buy_cost(pct)["present_worth_cost"]
        sens.append({"Resale value (% of price)": f"{pct:.0f}%", "Buy net cost (PW)": fmt(cur, pw),
                     "Lease advantage (PW)": fmt(cur, pw - lease["present_worth_cost"])})
    st.dataframe(pd.DataFrame(sens), hide_index=True)
    st.caption("Positive 'Lease advantage' means leasing costs less. Excludes insurance, maintenance, registration and "
               "wear-and-tear charges, which can differ between the two options.")
