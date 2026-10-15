"""Equipment Life-Cycle Cost Analysis (LCCA): baseline vs alternative."""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import caption, fmt, info, success

_CHILLER_A = dict(name="Standard-efficiency chiller", cost=180000.0, rebate=0.0, kw=300.0, lf=60.0, hours=4000.0,
                  maint=6000.0, oh_cost=30000.0, oh_year=10, salvage=10000.0)
_CHILLER_B = dict(name="High-efficiency chiller (VSD)", cost=260000.0, rebate=15000.0, kw=250.0, lf=60.0, hours=4000.0,
                  maint=5000.0, oh_cost=30000.0, oh_year=12, salvage=15000.0)

PRESETS = {
    "Chiller: standard vs high-efficiency": {
        "g": dict(study=20, rate=8.0, esc_e=3.0, esc_m=3.0, elec=0.10, demand=8.0),
        "A": _CHILLER_A, "B": _CHILLER_B,
    },
    "Air compressor: fixed-speed vs VFD": {
        "g": dict(study=15, rate=8.0, esc_e=3.0, esc_m=3.0, elec=0.10, demand=8.0),
        "A": dict(name="Fixed-speed (load/unload) compressor", cost=45000.0, rebate=0.0, kw=75.0, lf=85.0, hours=6000.0,
                  maint=4500.0, oh_cost=12000.0, oh_year=8, salvage=3000.0),
        "B": dict(name="VFD compressor", cost=70000.0, rebate=6000.0, kw=75.0, lf=62.0, hours=6000.0,
                  maint=4000.0, oh_cost=12000.0, oh_year=8, salvage=4000.0),
    },
    "Custom equipment": {
        "g": dict(study=20, rate=8.0, esc_e=3.0, esc_m=3.0, elec=0.10, demand=8.0),
        "A": {**_CHILLER_A, "name": "Option A (baseline)"}, "B": {**_CHILLER_B, "name": "Option B (alternative)"},
    },
}


def _inputs(label: str, d: dict, cur: str, pk: str, opt: str) -> dict:
    k = lambda f: f"lcca_{pk}_{opt}_{f}"
    st.subheader(label)
    o = {"name": st.text_input("Name", d["name"], key=k("name"))}
    o["cost"] = st.number_input(f"Installed Cost ({cur})", min_value=0.0, value=d["cost"], step=5000.0, key=k("cost"))
    o["rebate"] = st.number_input(f"Utility Rebate / Incentive ({cur})", min_value=0.0, value=d["rebate"], step=1000.0, key=k("rebate"),
                                  help="Upfront incentive that reduces the net first cost.")
    o["kw"] = st.number_input("Rated Electrical Input (kW)", min_value=0.0, value=d["kw"], step=5.0, key=k("kw"))
    o["lf"] = st.number_input("Average Load Factor (%)", min_value=0.0, max_value=100.0, value=d["lf"], step=1.0, key=k("lf"))
    o["hours"] = st.number_input("Operating Hours per Year", min_value=0.0, max_value=8760.0, value=d["hours"], step=100.0, key=k("hours"))
    o["maint"] = st.number_input(f"Annual Maintenance, Year 1 ({cur})", min_value=0.0, value=d["maint"], step=500.0, key=k("maint"))
    o["oh_cost"] = st.number_input(f"Major Overhaul / Replacement Cost ({cur})", min_value=0.0, value=d["oh_cost"], step=1000.0, key=k("oh_cost"))
    o["oh_year"] = st.number_input("Overhaul Year (0 = none)", min_value=0, max_value=50, value=d["oh_year"], step=1, key=k("oh_year"))
    o["salvage"] = st.number_input(f"Salvage / Residual Value at End of Study ({cur})", min_value=0.0, value=d["salvage"], step=1000.0, key=k("salvage"))
    return o


def _flows(o: dict, n: int, esc_e: float, esc_m: float, elec: float, demand: float, energy_factor: float = 1.0) -> pd.DataFrame:
    energy1, _ = calc.annual_energy_cost(o["kw"], o["lf"], o["hours"], elec, demand)
    return calc.lcc_cash_flows(o["cost"], o["rebate"], energy1 * energy_factor, o["maint"], o["oh_cost"],
                               int(o["oh_year"]), o["salvage"], n, esc_e, esc_m)


def render(cur: str) -> None:
    st.header("🏭 Equipment Life-Cycle Cost Analysis (LCCA)")
    st.markdown("Compare a baseline against a higher-efficiency alternative on **total cost of ownership**, not first cost: "
                "energy (with demand charges), maintenance, overhaul, rebates and residual value, discounted to present worth.")

    preset = st.selectbox("Equipment scenario", list(PRESETS), key="lcca_preset")
    pk = str(list(PRESETS).index(preset))
    p = PRESETS[preset]

    with st.expander("Study & utility assumptions", expanded=True):
        a, b, c = st.columns(3)
        n = a.slider("Study Period (Years)", 5, 40, p["g"]["study"], key=f"lcca_{pk}_study")
        rate = a.number_input("Discount Rate / MARR (%)", min_value=0.0, max_value=30.0, value=p["g"]["rate"], step=0.5, key=f"lcca_{pk}_rate")
        elec = b.number_input(f"Electricity Rate ({cur}/kWh)", min_value=0.0, value=p["g"]["elec"], step=0.01, format="%.3f", key=f"lcca_{pk}_elec")
        demand = b.number_input(f"Demand Charge ({cur}/kW-month)", min_value=0.0, value=p["g"]["demand"], step=1.0, key=f"lcca_{pk}_demand")
        esc_e = c.number_input("Energy Cost Escalation (%/yr)", min_value=0.0, max_value=20.0, value=p["g"]["esc_e"], step=0.5, key=f"lcca_{pk}_esce")
        esc_m = c.number_input("Maintenance Escalation (%/yr)", min_value=0.0, max_value=20.0, value=p["g"]["esc_m"], step=0.5, key=f"lcca_{pk}_escm")

    left, right = st.columns(2)
    with left:
        A = _inputs("Option A: Baseline", p["A"], cur, pk, "A")
    with right:
        B = _inputs("Option B: Alternative", p["B"], cur, pk, "B")

    dfA = _flows(A, n, esc_e, esc_m, elec, demand)
    dfB = _flows(B, n, esc_e, esc_m, elec, demand)
    sA, sB = calc.lcc_summary(dfA, rate), calc.lcc_summary(dfB, rate)
    inc = calc.incremental_analysis(dfA, dfB, rate)
    _, kwhA = calc.annual_energy_cost(A["kw"], A["lf"], A["hours"], elec, demand)
    _, kwhB = calc.annual_energy_cost(B["kw"], B["lf"], B["hours"], elec, demand)

    st.markdown("---")
    diff = sA["Total"] - sB["Total"]
    if abs(diff) < 1:
        info("Both options have essentially the same life-cycle cost.")
    elif diff > 0:
        success(f"**{B['name']} has the lower life-cycle cost**, saving {fmt(cur, diff)} in present worth over {n} years "
                   f"({fmt(cur, sA['EUAC'] - sB['EUAC'])} per year equivalent).")
    else:
        success(f"**{A['name']} has the lower life-cycle cost**, saving {fmt(cur, -diff)} in present worth over {n} years "
                   f"({fmt(cur, sB['EUAC'] - sA['EUAC'])} per year equivalent).")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Life-Cycle Cost: Option A", fmt(cur, sA["Total"]), help="Present worth of all costs net of rebate and salvage.")
    m2.metric("Life-Cycle Cost: Option B", fmt(cur, sB["Total"]))
    m3.metric("EUAC: Option A", fmt(cur, sA["EUAC"], 0), help="Equivalent uniform annual cost of Option A.")
    m4.metric("EUAC: Option B", fmt(cur, sB["EUAC"], 0), help="Equivalent uniform annual cost of Option B.")

    first_cost_gap = (B["cost"] - B["rebate"]) - (A["cost"] - A["rebate"])
    p1, p2, p3, p4 = st.columns(4)
    sp, dp, rr = inc["simple_payback"], inc["discounted_payback"], inc["irr"]
    if first_cost_gap > 0:
        p1.metric("Simple Payback on Extra Cost", f"{sp:.1f} yrs" if sp is not None else "Never")
        p2.metric("Discounted Payback", f"{dp:.1f} yrs" if dp is not None else "Never")
        p3.metric("IRR on Extra Investment", f"{rr:.1f}%" if rr is not None else "n/a",
                  help="Compare with your discount rate / MARR: above it means the extra spend pays off.")
    else:
        caption("Option B costs no more than Option A up front, so payback and incremental IRR do not apply.")
    p4.metric("Annual kWh Saved by B", f"{kwhA - kwhB:,.0f}")

    comp = pd.DataFrame([{"Option": o["name"], "Component": c, f"Present Worth ({cur})": s[c]}
                         for o, s in ((A, sA), (B, sB)) for c in ["Initial", "Energy", "Maintenance", "Overhaul", "Salvage"]])
    st.plotly_chart(px.bar(comp, x="Option", y=f"Present Worth ({cur})", color="Component", barmode="relative",
                           title="Present-Worth Cost Breakdown (salvage plots as a credit)"))

    cum = pd.DataFrame({"Year": dfA["Year"], "Cumulative savings": inc["cumulative"],
                        "Cumulative discounted savings": inc["cumulative_discounted"]})
    fig = px.line(cum, x="Year", y=["Cumulative savings", "Cumulative discounted savings"], markers=True,
                  title=f"Cumulative Savings of {B['name']} vs {A['name']}", labels={"value": f"Savings ({cur})", "variable": ""})
    fig.add_hline(y=0, line_dash="dot")
    st.plotly_chart(fig)

    st.subheader("Sensitivity: how robust is the decision?")
    caption("Present-worth advantage of Option B over Option A. Positive (green) = B has the lower life-cycle cost.")
    rates = sorted({max(0.0, rate + d) for d in (-4, -2, 0, 2, 4)})
    changes = [-20, -10, 0, 10, 20, 40]
    z = []
    for r in rates:
        z.append([calc.lcc_summary(_flows(A, n, esc_e, esc_m, elec, demand, 1 + ch / 100), r)["Total"]
                  - calc.lcc_summary(_flows(B, n, esc_e, esc_m, elec, demand, 1 + ch / 100), r)["Total"] for ch in changes])
    heat = px.imshow(z, x=[f"{c:+d}%" for c in changes], y=[f"{r:g}%" for r in rates], text_auto=".3s", aspect="auto",
                     color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                     labels={"x": "Change in energy cost", "y": "Discount rate", "color": f"PW advantage ({cur})"})
    st.plotly_chart(heat)

    st.subheader("📋 Year-by-Year Cash Flows")
    table = pd.DataFrame({"Year": dfA["Year"], f"{A['name']}": dfA["Total"], f"{B['name']}": dfB["Total"],
                          "Savings of B vs A": inc["savings"]})
    money = cur + "{:,.0f}"
    st.dataframe(table.style.format({c: money for c in table.columns if c != "Year"}), hide_index=True)
    st.download_button("📥 Export Cash Flows (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name="lcca_cash_flows.csv", mime="text/csv")
    caption("Before-tax analysis over a common study period; salvage values represent the equipment's remaining value at the "
               "end of the study. Energy and maintenance costs escalate from year 2. Illustrative defaults - replace with quotes "
               "and your utility tariff.")
