"""Replacement analysis: defender (existing asset) vs challenger (new asset)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules import calc
from modules.common import fmt

PRESETS = {
    "Air compressor: aging vs new": {
        "g": dict(rate=8.0),
        "D": dict(name="Existing compressor (defender)", proceeds=8000.0, energy=38000.0, maint=9000.0, down=6000.0,
                  growth=10.0, decline=15.0, life=8),
        "C": dict(name="New VFD compressor (challenger)", cost=70000.0, rebate=6000.0, energy=28000.0, maint=4000.0,
                  down=1000.0, growth=3.0, decline=12.0, life=15),
    },
    "Production machine: old vs new CNC": {
        "g": dict(rate=10.0),
        "D": dict(name="Existing machine (defender)", proceeds=60000.0, energy=8000.0, maint=10000.0, down=8000.0,
                  growth=8.0, decline=10.0, life=8),
        "C": dict(name="New machine (challenger)", cost=250000.0, rebate=0.0, energy=6000.0, maint=5000.0,
                  down=4000.0, growth=4.0, decline=10.0, life=12),
    },
    "Custom equipment": {
        "g": dict(rate=8.0),
        "D": dict(name="Existing asset (defender)", proceeds=8000.0, energy=38000.0, maint=9000.0, down=6000.0,
                  growth=10.0, decline=15.0, life=8),
        "C": dict(name="New asset (challenger)", cost=70000.0, rebate=6000.0, energy=28000.0, maint=4000.0,
                  down=1000.0, growth=3.0, decline=12.0, life=15),
    },
}


def _yrs(n: int) -> str:
    return f"{n} yr" if n == 1 else f"{n} yrs"


def _asset(label: str, d: dict, cur: str, pk: str, opt: str, defender: bool) -> dict:
    k = lambda f: f"rp_{pk}_{opt}_{f}"
    st.subheader(label)
    o = {"name": st.text_input("Name", d["name"], key=k("name"))}
    if defender:
        o["capital"] = st.number_input(f"Net Sale Proceeds if Replaced Today ({cur})", min_value=0.0, value=d["proceeds"], step=1000.0,
                                       key=k("cap"), help="What you could sell it for now, net of removal cost. Its original price "
                                                          "and book value are sunk costs and are ignored.")
    else:
        cost = st.number_input(f"Installed First Cost ({cur})", min_value=0.0, value=d["cost"], step=5000.0, key=k("cost"))
        rebate = st.number_input(f"Utility Rebate / Incentive ({cur})", min_value=0.0, value=d["rebate"], step=1000.0, key=k("rebate"))
        o["capital"] = max(0.0, cost - rebate)
        o["rebate"] = rebate
    o["energy"] = st.number_input(f"Energy Cost, Year 1 ({cur})", min_value=0.0, value=d["energy"], step=1000.0, key=k("energy"))
    o["maint"] = st.number_input(f"Maintenance Cost, Year 1 ({cur})", min_value=0.0, value=d["maint"], step=500.0, key=k("maint"))
    o["down"] = st.number_input(f"Downtime / Reliability Cost, Year 1 ({cur})", min_value=0.0, value=d["down"], step=500.0, key=k("down"),
                                help="Lost production, scrap and emergency repairs expected from unplanned stoppages.")
    o["growth"] = st.number_input("Annual Cost Growth (%)", min_value=0.0, max_value=50.0, value=d["growth"], step=0.5, key=k("growth"),
                                  help="How fast operating costs rise each year as the asset ages.")
    o["decline"] = st.number_input("Market Value Decline (%/yr)", min_value=0.0, max_value=60.0, value=d["decline"], step=1.0, key=k("decl"))
    o["life"] = st.slider("Maximum Years of Service" if not defender else "Maximum Remaining Years of Service", 2, 30, d["life"], key=k("life"))
    o["annual"] = o["energy"] + o["maint"] + o["down"]
    return o


def render(cur: str) -> None:
    st.header("🔄 Replacement Analysis: Defender vs Challenger")
    st.markdown("Should you keep the existing equipment or replace it now? This compares the **minimum equivalent uniform annual cost "
                "(EUAC)** of each option, finds each asset's **economic life**, and ignores sunk costs, as engineering economy requires.")

    preset = st.selectbox("Equipment scenario", list(PRESETS), key="rp_preset")
    pk = str(list(PRESETS).index(preset))
    p = PRESETS[preset]
    rate = st.number_input("Discount Rate / MARR (%)", min_value=0.0, max_value=30.0, value=p["g"]["rate"], step=0.5, key=f"rp_{pk}_rate")

    left, right = st.columns(2)
    with left:
        D = _asset("Defender (existing)", p["D"], cur, pk, "D", True)
    with right:
        C = _asset("Challenger (new)", p["C"], cur, pk, "C", False)

    dt = calc.retention_table(D["capital"], D["annual"], D["growth"], D["decline"], D["life"], rate)
    ct = calc.retention_table(C["capital"], C["annual"], C["growth"], C["decline"], C["life"], rate)
    res = calc.replacement_decision(dt, ct)

    st.markdown("---")
    if res["replace_now"]:
        st.success(f"**Replace now.** {C['name']} costs {fmt(cur, res['annual_advantage'], 0)} less per year "
                   f"(EUAC {fmt(cur, res['challenger_euac'], 0)} vs {fmt(cur, res['defender_euac'], 0)}).")
    else:
        st.success(f"**Keep the defender for now.** {D['name']} costs {fmt(cur, res['annual_advantage'], 0)} less per year "
                   f"(EUAC {fmt(cur, res['defender_euac'], 0)} vs {fmt(cur, res['challenger_euac'], 0)}). "
                   "Re-run this analysis each year as its costs and resale value change.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Defender Min EUAC", fmt(cur, res["defender_euac"], 0))
    m2.metric("Defender Economic Life", _yrs(res["defender_life"]))
    m3.metric("Challenger Min EUAC", fmt(cur, res["challenger_euac"], 0))
    m4.metric("Challenger Economic Life", _yrs(res["challenger_life"]))

    be = calc.breakeven_challenger_capital(res["defender_euac"], C["annual"], C["growth"], C["decline"], C["life"], rate)
    if be is None:
        st.info("Even a free challenger would cost more per year to operate than the defender, so replacement is never justified on these assumptions.")
    else:
        price = be + C.get("rebate", 0.0)
        st.info(f"**Break-even:** replacement pays off if the challenger's installed cost is below about **{fmt(cur, price, 0)}** "
                f"(net of rebate {fmt(cur, be, 0)}). Current: {fmt(cur, C['capital'] + C.get('rebate', 0.0), 0)}.")

    curves = pd.concat([dt.assign(Asset=D["name"]), ct.assign(Asset=C["name"])])
    st.plotly_chart(px.line(curves, x="Years Kept", y="EUAC", color="Asset", markers=True,
                            title="EUAC by Years Kept (the lowest point is the economic life)",
                            labels={"EUAC": f"EUAC ({cur})"}))

    fig = px.line(dt, x="Years Kept", y="Marginal Cost of Year", markers=True,
                  title=f"Defender: Cost of Keeping It One More Year vs Challenger's Best EUAC",
                  labels={"Marginal Cost of Year": f"Cost ({cur})"})
    fig.add_hline(y=res["challenger_euac"], line_dash="dash", annotation_text="Challenger min EUAC")
    st.plotly_chart(fig)
    st.caption("Where the defender's yearly cost rises above the dashed line, holding on one more year costs more than "
               "running the new asset.")

    money = cur + "{:,.0f}"
    t1, t2 = st.tabs(["Defender by years kept", "Challenger by years kept"])
    for tab, tbl in ((t1, dt), (t2, ct)):
        with tab:
            st.dataframe(tbl.style.format({c: money for c in tbl.columns if c != "Years Kept"}), hide_index=True)
    st.caption("Market value is assumed to fall by a constant percentage each year; operating costs grow at the stated rate. "
               "Before-tax analysis. Illustrative defaults: replace with your maintenance history, quotes and resale estimates.")
