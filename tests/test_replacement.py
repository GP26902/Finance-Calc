import pytest
from modules import calc

ARGS = dict(annual_cost_yr1=5_000, growth_pct=10.0, mv_decline_pct=15.0, max_years=10, rate_pct=8.0)


def test_one_year_euac_equals_marginal_cost_of_year_one():
    t = calc.retention_table(100_000, **ARGS)
    assert t["EUAC"].iloc[0] == pytest.approx(t["Marginal Cost of Year"].iloc[0])
    assert t["Marginal Cost of Year"].iloc[0] == pytest.approx(100_000 * 1.08 - 85_000 + 5_000)


def test_pw_of_marginal_costs_equals_pw_of_total_cost():
    t = calc.retention_table(100_000, **ARGS)
    for k in (1, 4, 10):
        pw_marg = sum(m * 1.08 ** -y for y, m in zip(t["Years Kept"][:k], t["Marginal Cost of Year"][:k]))
        pw_total = t["EUAC"].iloc[k - 1] / calc.ap_factor(0.08, k)
        assert pw_marg == pytest.approx(pw_total)


def test_no_depreciation_no_growth_euac_is_interest_plus_operating_cost():
    t = calc.retention_table(50_000, 4_000, 0.0, 0.0, 6, 8.0)
    assert t["EUAC"].tolist() == pytest.approx([50_000 * 0.08 + 4_000] * 6)


def test_economic_life_picks_minimum_euac():
    # steep early value loss (20%/yr) plus 10%/yr O&M growth gives a U-shaped EUAC curve
    t = calc.retention_table(100_000, 5_000, 10.0, 20.0, 25, 8.0)
    yrs, euac = calc.economic_life(t)
    assert euac == pytest.approx(t["EUAC"].min())
    assert 1 < yrs < 25
    assert t["EUAC"].iloc[0] > euac and t["EUAC"].iloc[-1] > euac
    # slow value loss with fast O&M growth: keeping the asset one year is already cheapest
    assert calc.economic_life(calc.retention_table(100_000, 5_000, 25.0, 5.0, 12, 8.0))[0] == 1


def test_decision_and_tie_keeps_defender():
    d = calc.retention_table(8_000, 42_000, 10.0, 15.0, 8, 8.0)
    c_cheap = calc.retention_table(30_000, 20_000, 3.0, 12.0, 15, 8.0)
    assert calc.replacement_decision(d, c_cheap)["replace_now"] is True
    assert calc.replacement_decision(d, d)["replace_now"] is False


def test_breakeven_capital_equalizes_euac():
    d = calc.retention_table(8_000, 42_000, 10.0, 15.0, 8, 8.0)
    d_euac = calc.economic_life(d)[1]
    cap = calc.breakeven_challenger_capital(d_euac, 32_000, 3.0, 12.0, 15, 8.0)
    assert cap is not None and cap > 0
    t = calc.retention_table(cap, 32_000, 3.0, 12.0, 15, 8.0)
    assert calc.economic_life(t)[1] == pytest.approx(d_euac, rel=1e-6)


def test_breakeven_none_when_challenger_operating_cost_alone_too_high():
    assert calc.breakeven_challenger_capital(10_000, 50_000, 3.0, 12.0, 15, 8.0) is None
