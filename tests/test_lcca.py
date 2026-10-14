import pytest
from modules import calc


def test_annual_energy_cost():
    cost, kwh = calc.annual_energy_cost(300, 60, 4000, 0.10, 8)
    assert kwh == pytest.approx(720_000)
    assert cost == pytest.approx(72_000 + 300 * 8 * 12)


def test_lcc_no_escalation_no_discount_is_simple_sum():
    df = calc.lcc_cash_flows(180_000, 5_000, 70_000, 6_000, 30_000, 10, 10_000, 20)
    s = calc.lcc_summary(df, 0.0)
    assert s["Total"] == pytest.approx(175_000 + 20 * 76_000 + 30_000 - 10_000)
    assert s["EUAC"] == pytest.approx(s["Total"] / 20)


def test_energy_pw_matches_closed_form_growing_annuity():
    n, i, g, a = 20, 0.08, 0.03, 50_000
    df = calc.lcc_cash_flows(0, 0, a, 0, 0, 0, 0, n, energy_esc_pct=3.0)
    closed = a / (i - g) * (1 - ((1 + g) / (1 + i)) ** n)
    assert calc.lcc_summary(df, 8.0)["Energy"] == pytest.approx(closed, rel=1e-9)


def test_overhaul_after_study_period_is_ignored_and_zero_means_none():
    assert calc.lcc_cash_flows(0, 0, 0, 0, 5_000, 25, 0, 20)["Overhaul"].sum() == 0
    assert calc.lcc_cash_flows(0, 0, 0, 0, 5_000, 0, 0, 20)["Overhaul"].sum() == 0
    assert calc.lcc_cash_flows(0, 0, 0, 0, 5_000, 20, 0, 20)["Overhaul"].sum() == 5_000


def test_irr_and_payback():
    assert calc.irr([-100, 110]) == pytest.approx(10.0, abs=1e-6)
    assert calc.irr([-1000, 300, 300, 300, 300, 300]) == pytest.approx(15.24, abs=0.01)
    assert calc.irr([100, 100, 100]) is None
    assert calc.payback_year([-100, -40, 20]) == pytest.approx(1 + 40 / 60)
    assert calc.payback_year([-100, -90, -80]) is None
    assert calc.payback_year([5, 10]) == 0.0


def test_incremental_pw_equals_difference_of_lcc():
    a = calc.lcc_cash_flows(180_000, 0, 72_000, 6_000, 30_000, 10, 10_000, 20, 3, 3)
    b = calc.lcc_cash_flows(260_000, 15_000, 60_000, 5_000, 30_000, 12, 15_000, 20, 3, 3)
    inc = calc.incremental_analysis(a, b, 8.0)
    assert inc["pw_savings"] == pytest.approx(calc.lcc_summary(a, 8.0)["Total"] - calc.lcc_summary(b, 8.0)["Total"])
    assert inc["irr"] is not None and inc["irr"] > 8.0   # worthwhile premium
    assert inc["simple_payback"] < inc["discounted_payback"]


def test_irr_makes_incremental_npw_zero():
    a = calc.lcc_cash_flows(100_000, 0, 30_000, 0, 0, 0, 0, 10)
    b = calc.lcc_cash_flows(150_000, 0, 20_000, 0, 0, 0, 0, 10)
    inc = calc.incremental_analysis(a, b, 8.0)
    assert calc.present_worth_of(inc["savings"], inc["irr"]) == pytest.approx(0, abs=1e-4)
