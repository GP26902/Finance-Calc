"""Energy-retrofit payback: LED lighting and VFD upgrades."""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import caption, fmt, success, warning

PRESETS = {
    "LED lighting retrofit": dict(unit="fixtures", qty=120, kw_before=0.46, kw_after=0.15, hours=4500.0, cost=320.0,
                                  rebate=60.0, maint=18.0, life=10, vfd=False,
                                  before_help="e.g. 400 W metal-halide high-bay including ballast losses",
                                  after_help="e.g. 150 W LED high-bay"),
    "VFD on pump / fan motors": dict(unit="motors", qty=4, kw_before=34.0, kw_after=21.1, hours=6000.0, cost=14000.0,
                                     rebate=2500.0, maint=300.0, life=15, vfd=True, full_kw=40.0, speed=80.0, drive_eff=97.0,
                                     before_help="Constant-speed motor throttled by a valve or damper, average input kW",
                                     after_help="Average input kW with the drive"),
    "Custom retrofit": dict(unit="units", qty=10, kw_before=5.0, kw_after=3.5, hours=4000.0, cost=3000.0,
                            rebate=0.0, maint=0.0, life=10, vfd=False, before_help="", after_help=""),
}


def _params(base: dict, **over) -> dict:
    return {**base, **over}


def render(cur: str) -> None:
    st.header("💡 Energy Retrofit Payback (LED / VFD)")
    st.markdown("Evaluate an efficiency upgrade the way a facilities or plant engineer would: energy and demand savings, "
                "utility rebates, payback, IRR, savings-to-investment ratio and the cost of the energy you save.")

    preset = st.selectbox("Retrofit type", list(PRESETS), key="rf_preset")
    pk = str(list(PRESETS).index(preset))
    p = PRESETS[preset]
    k = lambda f: f"rf_{pk}_{f}"

    with st.expander("Equipment & project inputs", expanded=True):
        a, b = st.columns(2)
        qty = a.number_input(f"Number of {p['unit']}", min_value=1, max_value=100000, value=p["qty"], step=1, key=k("qty"))
        hours = a.number_input("Operating Hours per Year", min_value=0.0, max_value=8760.0, value=p["hours"], step=100.0, key=k("hours"))
        kw_before = a.number_input("Existing Average Input Power per Unit (kW)", min_value=0.0, value=p["kw_before"], step=0.01,
                                   format="%.2f", key=k("kwb"), help=p["before_help"] or None)
        if p["vfd"]:
            use_aff = b.checkbox("Calculate proposed power from speed (affinity laws)", value=True, key=k("aff"))
        else:
            use_aff = False
        if use_aff:
            full_kw = b.number_input("Motor Full-Load Input Power (kW)", min_value=0.0, value=p["full_kw"], step=1.0, key=k("fkw"))
            speed = b.slider("Average Operating Speed (% of full speed)", 30, 100, int(p["speed"]), key=k("speed"),
                             help="Pump/fan power falls with the cube of speed, so a modest speed reduction saves a lot.")
            eff = b.number_input("Drive Efficiency (%)", min_value=80.0, max_value=100.0, value=p["drive_eff"], step=0.5, key=k("eff"))
            kw_after = calc.vfd_power_kw(full_kw, speed, eff)
            b.caption(f"Proposed average power: **{kw_after:.2f} kW** per motor")
        else:
            kw_after = b.number_input("Proposed Average Input Power per Unit (kW)", min_value=0.0, value=p["kw_after"], step=0.01,
                                      format="%.2f", key=k("kwa"), help=p["after_help"] or None)
        cost = a.number_input(f"Installed Cost per Unit, equipment + labor ({cur})", min_value=0.0, value=p["cost"], step=50.0, key=k("cost"))
        rebate = b.number_input(f"Utility Rebate per Unit ({cur})", min_value=0.0, value=p["rebate"], step=10.0, key=k("rebate"))
        maint = b.number_input(f"Maintenance Savings per Unit per Year ({cur})", min_value=0.0, value=p["maint"], step=5.0, key=k("maint"),
                               help="e.g. avoided lamp/ballast replacement labor.")
        n = a.slider("Analysis Period (Years)", 3, 30, p["life"], key=k("life"),
                     help="Use the equipment's useful life. LED: rated hours / annual hours.")

    with st.expander("Utility & financial assumptions", expanded=True):
        a, b, c = st.columns(3)
        elec = a.number_input(f"Electricity Rate ({cur}/kWh)", min_value=0.0, value=0.10, step=0.01, format="%.3f", key=k("elec"))
        demand = a.number_input(f"Demand Charge ({cur}/kW-month)", min_value=0.0, value=8.0, step=1.0, key=k("demand"))
        coinc = b.number_input("Demand Coincidence Factor (%)", min_value=0.0, max_value=100.0, value=80.0, step=5.0, key=k("coinc"),
                               help="Share of the kW reduction that is present at your billing peak. Lighting that is on at peak is near 100%.")
        rate = b.number_input("Discount Rate / MARR (%)", min_value=0.0, max_value=30.0, value=8.0, step=0.5, key=k("rate"))
        esc_e = c.number_input("Energy Cost Escalation (%/yr)", min_value=0.0, max_value=20.0, value=3.0, step=0.5, key=k("esce"))
        esc_m = c.number_input("Maintenance Escalation (%/yr)", min_value=0.0, max_value=20.0, value=3.0, step=0.5, key=k("escm"))
        ef = c.number_input("Grid Emission Factor (kg CO2/kWh)", min_value=0.0, max_value=2.0, value=0.37, step=0.01, key=k("ef"),
                            help="Illustrative US-average value; use your region's EPA eGRID figure.")

    scen = st.slider("What if utility rates change? (applies to electricity and demand charges)", -30, 50, 0, 5, format="%d%%", key=k("scen"))
    f = 1 + scen / 100

    if kw_after >= kw_before:
        warning("The proposed power must be lower than the existing power for the retrofit to save energy.")
        return

    base = dict(qty=qty, kw_before=kw_before, kw_after=kw_after, hours=hours, elec_rate=elec * f, demand_charge=demand * f,
                coincidence_pct=coinc, cost_per_unit=cost, rebate_per_unit=rebate, maint_save_per_unit=maint, n=n,
                rate_pct=rate, esc_e_pct=esc_e, esc_m_pct=esc_m, emission_kg_per_kwh=ef)
    r = calc.retrofit_analysis(**base)

    st.markdown("---")
    if r["npw"] > 0:
        success(f"**This retrofit adds value:** NPW of {fmt(cur, r['npw'])} over {n} years at a {rate:g}% discount rate.")
    else:
        warning(f"**This retrofit does not earn the {rate:g}% hurdle rate** (NPW {fmt(cur, r['npw'])}) with these inputs.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net Investment", fmt(cur, r["net_cost"], 0))
    m2.metric("Year-1 Savings", fmt(cur, r["savings_yr1"], 0))
    m3.metric("Energy Saved per Year", f"{r['kwh_saved']:,.0f} kWh")
    m4.metric("CO2 Avoided per Year", f"{r['co2_tonnes_per_year']:,.1f} t")

    sp, dp, rr, sir, cse = r["simple_payback"], r["discounted_payback"], r["irr"], r["sir"], r["cost_of_saved_energy"]
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Simple Payback", f"{sp:.1f} yrs" if sp is not None else "Never")
    m6.metric("Discounted Payback", f"{dp:.1f} yrs" if dp is not None else "Never")
    m7.metric("IRR", f"{rr:.1f}%" if rr is not None else "n/a")
    m8.metric("Net Present Worth", fmt(cur, r["npw"], 0))
    m9, m10, _ = st.columns(3)
    m9.metric("Savings-to-Investment Ratio", f"{sir:.2f}" if sir is not None else "n/a",
              help="PW of savings / net investment. Above 1.0 means the project pays for itself in present-worth terms.")
    m10.metric("Cost of Saved Energy", f"{fmt(cur, cse, 3)}/kWh" if cse is not None else "n/a",
               help="Levelized cost of each kWh saved. Compare with your electricity rate.")
    caption(f"Reduction: {r['kw_saved']:,.1f} kW total | year-1 energy and demand savings {fmt(cur, r['energy_savings_yr1'], 0)} | "
               f"maintenance savings {fmt(cur, r['maint_savings_yr1'], 0)}")

    df = r["flows"]
    cum = pd.DataFrame({"Year": df["Year"], "Cumulative cash flow": r["cumulative"],
                        "Cumulative discounted": r["cumulative_discounted"]})
    fig = px.line(cum, x="Year", y=["Cumulative cash flow", "Cumulative discounted"], markers=True,
                  title="Cumulative Cash Flow (crossing zero = payback)", labels={"value": f"Cash ({cur})", "variable": ""})
    fig.add_hline(y=0, line_dash="dot")
    st.plotly_chart(fig)

    sav = df[df["Year"] > 0].melt(id_vars="Year", value_vars=["Energy Savings", "Maintenance Savings"],
                                   var_name="Source", value_name=f"Savings ({cur})")
    st.plotly_chart(px.bar(sav, x="Year", y=f"Savings ({cur})", color="Source", barmode="stack", title="Annual Savings by Source"))

    st.subheader("Sensitivity: what drives the result?")
    caption("Change in NPW when each input moves 20% below or above its current value.")
    base_npw = r["npw"]
    drivers = [
        ("Electricity & demand rates", lambda x: _params(base, elec_rate=base["elec_rate"] * x, demand_charge=base["demand_charge"] * x)),
        ("Operating hours", lambda x: _params(base, hours=hours * x)),
        ("Installed cost", lambda x: _params(base, cost_per_unit=cost * x)),
        ("Power saved (kW)", lambda x: _params(base, kw_after=kw_before - (kw_before - kw_after) * x)),
        ("Discount rate", lambda x: _params(base, rate_pct=rate * x)),
    ]
    rows = []
    for name, fn in drivers:
        for label, x in (("-20%", 0.8), ("+20%", 1.2)):
            rows.append({"Driver": name, "Case": label,
                         f"Change in NPW ({cur})": calc.retrofit_analysis(**fn(x))["npw"] - base_npw})
    tor = pd.DataFrame(rows)
    order = tor.assign(a=tor[f"Change in NPW ({cur})"].abs()).groupby("Driver")["a"].max().sort_values().index.tolist()
    ft = px.bar(tor, y="Driver", x=f"Change in NPW ({cur})", color="Case", orientation="h", barmode="overlay",
                category_orders={"Driver": order}, title="Tornado Chart: Sensitivity of NPW")
    st.plotly_chart(ft)

    st.subheader("📋 Year-by-Year Cash Flows")
    money = cur + "{:,.0f}"
    st.dataframe(df.style.format({c: money for c in df.columns if c != "Year"}), hide_index=True)
    st.download_button("📥 Export Cash Flows (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="retrofit_cash_flows.csv", mime="text/csv")
    caption("Before-tax analysis. Illustrative defaults: replace with vendor quotes, measured power draw and your utility tariff.")
