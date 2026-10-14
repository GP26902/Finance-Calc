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
