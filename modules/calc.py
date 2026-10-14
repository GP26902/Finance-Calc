"""Pure calculation layer (no Streamlit imports) so every formula can be unit-tested.

Conventions: rates passed in as percentages (6.5 = 6.5 %), periods as integers,
cash flows in whatever currency the UI is showing.
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------- interest factors
def pa_factor(i: float, n: int) -> float:
    """(P/A, i, n): present worth of 1 per period for n periods."""
    if abs(i) < 1e-12:
        return float(n)
    return (1 - (1 + i) ** -n) / i


def ap_factor(i: float, n: int) -> float:
    """(A/P, i, n): uniform payment equivalent to a present amount of 1."""
    if abs(i) < 1e-12:
        return 1.0 / n
    return i / (1 - (1 + i) ** -n)


def pf_factor(i: float, n: int) -> float:
    """(P/F, i, n): present worth of 1 received n periods from now."""
    return (1 + i) ** -n


def fp_factor(i: float, n: int) -> float:
    """(F/P, i, n): future worth of 1 today."""
    return (1 + i) ** n


# ---------------------------------------------------------------- loans
def monthly_payment(principal: float, annual_rate_pct: float, n_months: int) -> float:
    if n_months <= 0:
        raise ValueError("n_months must be positive")
    return principal * ap_factor(annual_rate_pct / 100 / 12, n_months)


def loan_balance(principal: float, annual_rate_pct: float, n_months: int, after_months: int) -> float:
    """Outstanding balance after `after_months` payments (closed form)."""
    k = min(max(int(after_months), 0), n_months)
    r = annual_rate_pct / 100 / 12
    pmt = monthly_payment(principal, annual_rate_pct, n_months)
    if abs(r) < 1e-12:
        return max(0.0, principal - pmt * k)
    bal = principal * (1 + r) ** k - pmt * ((1 + r) ** k - 1) / r
    return max(0.0, bal) if bal > 1e-6 else 0.0


def amortization_schedule(principal: float, annual_rate_pct: float, n_months: int) -> pd.DataFrame:
    r = annual_rate_pct / 100 / 12
    pmt = monthly_payment(principal, annual_rate_pct, n_months)
    balance = principal
    rows = []
    for m in range(1, n_months + 1):
        interest = balance * r
        principal_paid = pmt - interest
        payment = pmt
        if m == n_months:  # absorb floating-point residue in the last payment
            principal_paid = balance
            payment = balance + interest
        balance -= principal_paid
        rows.append({
            "Month": m,
            "Total Monthly Payment": payment,
            "Principal Paid": principal_paid,
            "Interest Paid": interest,
            "Remaining Balance": max(0.0, balance) if balance > 1e-6 else 0.0,
        })
    return pd.DataFrame(rows)


def loan_summary(price: float, down: float, annual_rate_pct: float, years: int, fees: float) -> dict:
    principal = max(0.0, price - down)
    n = int(years) * 12
    pmt = monthly_payment(principal, annual_rate_pct, n)
    installments = pmt * n
    return {
        "principal": principal,
        "n_months": n,
        "monthly_payment": pmt,
        "total_interest": installments - principal,
        "total_cost": installments + down + fees,
        "down_pct": (down / price * 100) if price > 0 else 0.0,
        "effective_apr": effective_apr(principal, pmt, n, fees),
    }


def effective_apr(principal: float, payment: float, n_months: int, fees: float = 0.0):
    """Nominal annual rate (%, monthly compounding) that equates the payments to the
    cash actually received (principal - upfront fees). Returns None if undefined."""
    net = principal - fees
    if principal <= 0 or net <= 0 or payment * n_months < net:
        return None
    lo, hi = 0.0, 1.0
    if payment * pa_factor(hi, n_months) > net:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if payment * pa_factor(mid, n_months) > net:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 12 * 100


# ---------------------------------------------------------------- savings
def future_value(principal: float, rate_pct: float, periods_per_year: int, years: float,
                 rate_is_apy: bool = False) -> float:
    """Compound growth. If rate_is_apy, the quoted rate is already an effective annual
    yield, so the compounding frequency cannot change the answer."""
    n = periods_per_year
    if rate_is_apy:
        periodic = (1 + rate_pct / 100) ** (1 / n) - 1
    else:
        periodic = rate_pct / 100 / n
    return principal * (1 + periodic) ** (n * years)


def effective_annual_yield(nominal_pct: float, periods_per_year: int) -> float:
    return ((1 + nominal_pct / 100 / periods_per_year) ** periods_per_year - 1) * 100


# ---------------------------------------------------------------- depreciation
# IRS Pub. 946, Table A-1 (half-year convention), percent of cost per year.
MACRS_HALF_YEAR = {
    3: [33.33, 44.45, 14.81, 7.41],
    5: [20.00, 32.00, 19.20, 11.52, 11.52, 5.76],
    7: [14.29, 24.49, 17.49, 12.49, 8.93, 8.92, 8.93, 4.46],
    10: [10.00, 18.00, 14.40, 11.52, 9.22, 7.37, 6.55, 6.55, 6.56, 6.55, 3.28],
    15: [5.00, 9.50, 8.55, 7.70, 6.93, 6.23, 5.90, 5.90, 5.91, 5.90, 5.91, 5.90, 5.91, 5.90, 5.91, 2.95],
}


def _dep_table(cost: float, deps: list[float]) -> pd.DataFrame:
    rows = [{"Year": 0, "Depreciation": 0.0, "Accumulated Depreciation": 0.0, "Book Value": cost}]
    acc = 0.0
    for yr, d in enumerate(deps, start=1):
        acc += d
        rows.append({"Year": yr, "Depreciation": d, "Accumulated Depreciation": acc, "Book Value": cost - acc})
    return pd.DataFrame(rows)


def straight_line(cost: float, salvage: float, life: int) -> pd.DataFrame:
    return _dep_table(cost, [(cost - salvage) / life] * life)


def declining_balance(cost: float, salvage: float, life: int, factor: float = 2.0,
                      switch_to_sl: bool = True) -> pd.DataFrame:
    """Declining balance (factor 2.0 = DDB). Depreciation never takes book value below
    salvage, and optionally switches to straight-line when SL gives a larger deduction."""
    rate = factor / life
    book = cost
    deps = []
    for yr in range(1, life + 1):
        d = book * rate
        if switch_to_sl:
            d = max(d, (book - salvage) / (life - yr + 1))
        d = max(0.0, min(d, book - salvage))
        deps.append(d)
        book -= d
    return _dep_table(cost, deps)


def macrs(cost: float, recovery_class: int) -> pd.DataFrame:
    """MACRS, half-year convention. Salvage is ignored by the tax rules."""
    return _dep_table(cost, [cost * p / 100 for p in MACRS_HALF_YEAR[recovery_class]])


# ---------------------------------------------------------------- project worth
def project_worth(initial: float, annual: float, life: int, marr_pct: float, salvage: float = 0.0):
    """Returns (NPW, EUAW, FW) for an investment with uniform annual net benefit."""
    i = marr_pct / 100
    npw = -initial + annual * pa_factor(i, life) + salvage * pf_factor(i, life)
    return npw, npw * ap_factor(i, life), npw * fp_factor(i, life)


# ---------------------------------------------------------------- auto: buy vs lease
def lease_terms(cap_cost: float, residual: float, term_months: int, lease_apr_pct: float,
                tax_rate_pct: float = 0.0) -> dict:
    """Standard lease math: money factor = APR / 2400."""
    mf = lease_apr_pct / 2400
    depreciation = (cap_cost - residual) / term_months
    finance = (cap_cost + residual) * mf
    base = depreciation + finance
    tax = base * tax_rate_pct / 100
    return {"money_factor": mf, "depreciation": depreciation, "finance_charge": finance,
            "base_payment": base, "tax": tax, "payment": base + tax}


def lease_total_cost(price, down, residual, term_months, lease_apr_pct, tax_rate_pct,
                     acquisition_fee, disposition_fee, allowed_miles_yr, expected_miles_yr,
                     overage_per_mile, opp_rate_pct) -> dict:
    t = lease_terms(price - down, residual, term_months, lease_apr_pct, tax_rate_pct)
    overage = max(0.0, expected_miles_yr - allowed_miles_yr) * term_months / 12 * overage_per_mile
    upfront = down + acquisition_fee
    end = disposition_fee + overage
    rm = opp_rate_pct / 100 / 12
    return {
        **t,
        "upfront": upfront,
        "end_charges": end,
        "overage": overage,
        "nominal_cost": upfront + t["payment"] * term_months + end,
        "present_worth_cost": upfront + t["payment"] * pa_factor(rm, term_months) + end * pf_factor(rm, term_months),
        "monthly_equivalent": (upfront + t["payment"] * term_months + end) / term_months,
    }


def buy_total_cost(price, down, loan_apr_pct, loan_years, horizon_months, resale_value,
                   tax_rate_pct, fees, opp_rate_pct) -> dict:
    """Net cost of financing the purchase and selling at the end of the horizon."""
    principal = max(0.0, price - down)
    n = int(loan_years) * 12
    pmt = monthly_payment(principal, loan_apr_pct, n)
    pay_months = min(horizon_months, n)
    balance = loan_balance(principal, loan_apr_pct, n, horizon_months)
    upfront = down + price * tax_rate_pct / 100 + fees
    equity = resale_value - balance
    rm = opp_rate_pct / 100 / 12
    nominal = upfront + pmt * pay_months - equity
    return {
        "monthly_payment": pmt,
        "pay_months": pay_months,
        "upfront": upfront,
        "balance_at_end": balance,
        "equity": equity,
        "nominal_cost": nominal,
        "present_worth_cost": upfront + pmt * pa_factor(rm, pay_months) - equity * pf_factor(rm, horizon_months),
        "monthly_equivalent": nominal / horizon_months,
    }


# ---------------------------------------------------------------- lifecycle cost (LCCA)
def annual_energy_cost(rated_kw: float, load_factor_pct: float, hours_per_year: float,
                       rate_per_kwh: float, demand_charge_per_kw_month: float = 0.0):
    """Year-1 electricity cost and annual kWh. Demand charge is billed on rated kW
    (assumes the equipment runs at full rated input during the billing peak)."""
    kwh = rated_kw * load_factor_pct / 100 * hours_per_year
    cost = kwh * rate_per_kwh + rated_kw * demand_charge_per_kw_month * 12
    return cost, kwh


def lcc_cash_flows(initial: float, rebate: float, energy_yr1: float, maint_yr1: float,
                   overhaul_cost: float, overhaul_year: int, salvage: float, n: int,
                   energy_esc_pct: float = 0.0, maint_esc_pct: float = 0.0) -> pd.DataFrame:
    """Year-by-year cost table (costs positive, salvage negative). Year-1 energy and
    maintenance costs escalate from year 2 onward. overhaul_year = 0 means no overhaul."""
    ge, gm = energy_esc_pct / 100, maint_esc_pct / 100
    rows = []
    for t in range(0, n + 1):
        row = {
            "Year": t,
            "Initial": (initial - rebate) if t == 0 else 0.0,
            "Energy": energy_yr1 * (1 + ge) ** (t - 1) if t >= 1 else 0.0,
            "Maintenance": maint_yr1 * (1 + gm) ** (t - 1) if t >= 1 else 0.0,
            "Overhaul": overhaul_cost if (overhaul_year and t == overhaul_year) else 0.0,
            "Salvage": -salvage if t == n else 0.0,
        }
        row["Total"] = row["Initial"] + row["Energy"] + row["Maintenance"] + row["Overhaul"] + row["Salvage"]
        rows.append(row)
    return pd.DataFrame(rows)


def present_worth_of(series, rate_pct: float) -> float:
    i = rate_pct / 100
    return float(sum(v * (1 + i) ** -t for t, v in enumerate(series)))


def lcc_summary(df: pd.DataFrame, rate_pct: float) -> dict:
    """Present worth by cost component, total life-cycle cost and EUAC."""
    n = int(df["Year"].max())
    out = {c: present_worth_of(df[c], rate_pct) for c in ["Initial", "Energy", "Maintenance", "Overhaul", "Salvage", "Total"]}
    out["EUAC"] = out["Total"] * ap_factor(rate_pct / 100, n)
    return out


def irr(cash_flows, lo: float = -0.99, hi: float = 10.0):
    """Internal rate of return in %, by bisection. None if there is no sign change."""
    def npv(r):
        return sum(cf * (1 + r) ** -t for t, cf in enumerate(cash_flows))
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2 * 100


def payback_year(cumulative):
    """First time the cumulative cash flow reaches zero (linear interpolation within the year).
    0.0 if never negative; None if it never recovers."""
    cum = list(cumulative)
    if not cum:
        return None
    if cum[0] >= 0:
        return 0.0
    for t in range(1, len(cum)):
        if cum[t] >= 0:
            return (t - 1) + (-cum[t - 1]) / (cum[t] - cum[t - 1])
    return None


def incremental_analysis(df_base: pd.DataFrame, df_alt: pd.DataFrame, rate_pct: float) -> dict:
    """Alternative vs baseline: savings stream = baseline cost - alternative cost, by year."""
    savings = (df_base["Total"] - df_alt["Total"]).tolist()
    i = rate_pct / 100
    disc = [s * (1 + i) ** -t for t, s in enumerate(savings)]
    cum, cum_d, a, b = [], [], 0.0, 0.0
    for s, d in zip(savings, disc):
        a += s
        b += d
        cum.append(a)
        cum_d.append(b)
    return {
        "savings": savings,
        "cumulative": cum,
        "cumulative_discounted": cum_d,
        "pw_savings": sum(disc),
        "simple_payback": payback_year(cum),
        "discounted_payback": payback_year(cum_d),
        "irr": irr(savings),
    }


# ---------------------------------------------------------------- energy retrofit (LED / VFD)
def vfd_power_kw(full_load_kw: float, speed_pct: float, drive_efficiency_pct: float = 97.0) -> float:
    """Average input power of a variable-torque load (pump/fan) at reduced speed.
    Affinity laws: power scales with the cube of speed; the drive adds its own losses."""
    return full_load_kw * (speed_pct / 100) ** 3 / (drive_efficiency_pct / 100)


def retrofit_analysis(qty, kw_before, kw_after, hours, elec_rate, demand_charge, coincidence_pct,
                      cost_per_unit, rebate_per_unit, maint_save_per_unit, n, rate_pct,
                      esc_e_pct=0.0, esc_m_pct=0.0, emission_kg_per_kwh=0.0) -> dict:
    """Economics of an energy-efficiency retrofit; savings are year-1 values escalated from year 2."""
    kw_saved = qty * (kw_before - kw_after)
    kwh_saved = kw_saved * hours
    energy1 = kwh_saved * elec_rate + kw_saved * coincidence_pct / 100 * demand_charge * 12
    maint1 = qty * maint_save_per_unit
    net_cost = qty * (cost_per_unit - rebate_per_unit)
    ge, gm, i = esc_e_pct / 100, esc_m_pct / 100, rate_pct / 100

    rows = [{"Year": 0, "Investment": -net_cost, "Energy Savings": 0.0, "Maintenance Savings": 0.0,
             "Net Cash Flow": -net_cost}]
    for t in range(1, n + 1):
        e, m = energy1 * (1 + ge) ** (t - 1), maint1 * (1 + gm) ** (t - 1)
        rows.append({"Year": t, "Investment": 0.0, "Energy Savings": e, "Maintenance Savings": m,
                     "Net Cash Flow": e + m})
    df = pd.DataFrame(rows)

    net = df["Net Cash Flow"].tolist()
    disc = [v * (1 + i) ** -t for t, v in enumerate(net)]
    cum = df["Net Cash Flow"].cumsum().tolist()
    cum_d = pd.Series(disc).cumsum().tolist()
    npw = sum(disc)
    pw_savings = sum(disc[1:])
    return {
        "flows": df, "cumulative": cum, "cumulative_discounted": cum_d,
        "kw_saved": kw_saved, "kwh_saved": kwh_saved, "net_cost": net_cost,
        "energy_savings_yr1": energy1, "maint_savings_yr1": maint1, "savings_yr1": energy1 + maint1,
        "npw": npw, "euaw": npw * ap_factor(i, n),
        "simple_payback": payback_year(cum), "discounted_payback": payback_year(cum_d),
        "irr": irr(net),
        "sir": pw_savings / net_cost if net_cost > 0 else None,
        "cost_of_saved_energy": (net_cost * ap_factor(i, n) / kwh_saved) if (kwh_saved > 0 and net_cost > 0) else None,
        "co2_tonnes_per_year": kwh_saved * emission_kg_per_kwh / 1000,
    }


# ---------------------------------------------------------------- replacement analysis
def retention_table(capital: float, annual_cost_yr1: float, growth_pct: float, mv_decline_pct: float,
                    max_years: int, rate_pct: float) -> pd.DataFrame:
    """Cost of keeping an asset k years, k = 1..max_years.

    capital = money tied up in the asset today (challenger: net first cost; defender: what it
    could be sold for now, since its original price is sunk). Market value falls by a constant
    percentage each year; annual operating cost grows by growth_pct from year 2.
    Columns: operating cost in year k, market value at end of k, marginal cost of year k
    (the cost of holding the asset one more year) and EUAC if kept k years."""
    i, g, d = rate_pct / 100, growth_pct / 100, mv_decline_pct / 100
    rows, pw_ops, mv_prev = [], 0.0, capital
    for k in range(1, int(max_years) + 1):
        cost_k = annual_cost_yr1 * (1 + g) ** (k - 1)
        pw_ops += cost_k * (1 + i) ** -k
        mv_k = capital * (1 - d) ** k
        pw_total = capital + pw_ops - mv_k * (1 + i) ** -k
        rows.append({
            "Years Kept": k,
            "Operating Cost in Year": cost_k,
            "Market Value at End": mv_k,
            "Marginal Cost of Year": mv_prev * (1 + i) - mv_k + cost_k,
            "EUAC": pw_total * ap_factor(i, k),
        })
        mv_prev = mv_k
    return pd.DataFrame(rows)


def economic_life(table: pd.DataFrame):
    """(years, EUAC) of the retention period with the lowest EUAC."""
    idx = table["EUAC"].idxmin()
    return int(table.loc[idx, "Years Kept"]), float(table.loc[idx, "EUAC"])


def replacement_decision(defender: pd.DataFrame, challenger: pd.DataFrame) -> dict:
    """Compare minimum EUACs. A tie keeps the defender."""
    d_life, d_euac = economic_life(defender)
    c_life, c_euac = economic_life(challenger)
    return {"defender_life": d_life, "defender_euac": d_euac, "challenger_life": c_life,
            "challenger_euac": c_euac, "replace_now": c_euac < d_euac, "annual_advantage": abs(d_euac - c_euac)}


def breakeven_challenger_capital(defender_euac: float, annual_cost_yr1: float, growth_pct: float,
                                 mv_decline_pct: float, max_years: int, rate_pct: float):
    """Highest net first cost at which the challenger's minimum EUAC still equals the defender's.
    None if even a free challenger would cost more per year than the defender."""
    def gap(cap):
        return economic_life(retention_table(cap, annual_cost_yr1, growth_pct, mv_decline_pct, max_years, rate_pct))[1] - defender_euac
    if gap(0.0) >= 0:
        return None
    lo, hi = 0.0, max(1.0, defender_euac * max_years * 20)
    while gap(hi) < 0:
        hi *= 2
        if hi > 1e12:
            return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if gap(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
