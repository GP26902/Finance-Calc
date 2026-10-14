import pytest
from modules import calc

BASE = dict(qty=100, kw_before=0.40, kw_after=0.15, hours=4000, elec_rate=0.10, demand_charge=0.0,
            coincidence_pct=100, cost_per_unit=250, rebate_per_unit=0, maint_save_per_unit=0, n=10, rate_pct=0.0)


def test_vfd_affinity_laws():
    assert calc.vfd_power_kw(40, 100, 100) == pytest.approx(40)
    assert calc.vfd_power_kw(40, 80, 100) == pytest.approx(40 * 0.512)
    assert calc.vfd_power_kw(40, 80, 97) == pytest.approx(40 * 0.512 / 0.97)
    assert calc.vfd_power_kw(40, 50, 100) == pytest.approx(5.0)   # half speed = one-eighth power


def test_led_textbook_numbers_and_payback():
    r = calc.retrofit_analysis(**BASE)
    assert r["kw_saved"] == pytest.approx(25)
    assert r["kwh_saved"] == pytest.approx(100_000)
    assert r["energy_savings_yr1"] == pytest.approx(10_000)
    assert r["net_cost"] == pytest.approx(25_000)
    assert r["simple_payback"] == pytest.approx(2.5)
    assert r["npw"] == pytest.approx(10 * 10_000 - 25_000)   # 0 % discount rate
    assert r["sir"] == pytest.approx(4.0)
    assert r["cost_of_saved_energy"] == pytest.approx(25_000 / 10 / 100_000)


def test_demand_rebate_and_maintenance_savings():
    r = calc.retrofit_analysis(**{**BASE, "demand_charge": 10, "coincidence_pct": 80, "rebate_per_unit": 50,
                                  "maint_save_per_unit": 20})
    assert r["energy_savings_yr1"] == pytest.approx(10_000 + 25 * 0.8 * 10 * 12)
    assert r["maint_savings_yr1"] == pytest.approx(2_000)
    assert r["net_cost"] == pytest.approx(100 * 200)


def test_irr_zeroes_npw_and_discounting_lowers_npw():
    r = calc.retrofit_analysis(**{**BASE, "rate_pct": 8.0, "esc_e_pct": 3.0})
    assert r["irr"] > 8.0
    assert calc.present_worth_of(r["flows"]["Net Cash Flow"], r["irr"]) == pytest.approx(0, abs=1e-4)
    assert r["discounted_payback"] > r["simple_payback"]


def test_rebate_exceeding_cost_means_no_payback_metrics():
    r = calc.retrofit_analysis(**{**BASE, "rebate_per_unit": 300})
    assert r["net_cost"] < 0
    assert r["simple_payback"] == 0.0
    assert r["irr"] is None and r["sir"] is None and r["cost_of_saved_energy"] is None


def test_no_savings_never_pays_back():
    r = calc.retrofit_analysis(**{**BASE, "kw_after": 0.40})
    assert r["simple_payback"] is None
    assert r["npw"] < 0


def test_co2_avoided():
    r = calc.retrofit_analysis(**{**BASE, "emission_kg_per_kwh": 0.37})
    assert r["co2_tonnes_per_year"] == pytest.approx(100_000 * 0.37 / 1000)


def test_higher_discount_rate_lowers_npw_and_escalation_raises_it():
    n0 = calc.retrofit_analysis(**BASE)["npw"]
    n8 = calc.retrofit_analysis(**{**BASE, "rate_pct": 8.0})["npw"]
    n8e = calc.retrofit_analysis(**{**BASE, "rate_pct": 8.0, "esc_e_pct": 3.0})["npw"]
    assert n8 < n0
    assert n8e > n8
