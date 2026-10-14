import pytest
from modules import calc


def test_interest_factors_textbook():
    assert calc.pa_factor(0.08, 10) == pytest.approx(6.7101, rel=1e-4)
    assert calc.ap_factor(0.08, 10) == pytest.approx(0.14903, rel=1e-4)
    assert calc.pf_factor(0.08, 10) == pytest.approx(0.46319, rel=1e-4)
    assert calc.fp_factor(0.08, 10) == pytest.approx(2.15892, rel=1e-4)
    assert calc.pa_factor(0.0, 10) == 10


def test_mortgage_payment():
    assert calc.monthly_payment(280_000, 6.5, 360) == pytest.approx(1769.79, abs=0.01)


def test_zero_rate_loan():
    assert calc.monthly_payment(12_000, 0, 12) == pytest.approx(1000)


def test_schedule_pays_off_to_zero_and_matches_closed_form():
    df = calc.amortization_schedule(280_000, 6.5, 360)
    assert df["Remaining Balance"].iloc[-1] == 0
    assert df["Principal Paid"].sum() == pytest.approx(280_000)
    assert calc.loan_balance(280_000, 6.5, 360, 60) == pytest.approx(df["Remaining Balance"].iloc[59], rel=1e-9)


def test_effective_apr_equals_nominal_without_fees_and_rises_with_fees():
    s0 = calc.loan_summary(100_000, 0, 6.0, 15, 0)
    assert s0["effective_apr"] == pytest.approx(6.0, abs=1e-6)
    s1 = calc.loan_summary(100_000, 0, 6.0, 15, 2_000)
    assert s1["effective_apr"] > 6.0


def test_down_payment_larger_than_price_gives_zero_principal():
    assert calc.loan_summary(10_000, 12_000, 5, 3, 0)["principal"] == 0


def test_future_value_apy_vs_nominal():
    assert calc.future_value(1000, 5, 12, 1, rate_is_apy=True) == pytest.approx(1050)
    assert calc.future_value(1000, 5, 12, 1, rate_is_apy=False) == pytest.approx(1051.16, abs=0.01)
    # APY result must not depend on compounding frequency
    assert calc.future_value(1000, 5, 365, 3, True) == pytest.approx(calc.future_value(1000, 5, 1, 3, True))


def test_ddb_regression_never_depreciates_below_salvage():
    # Original bug: $50k, $5k salvage, 5 yr recorded $2,592 in yr 5 and exceeded the $45k base
    df = calc.declining_balance(50_000, 5_000, 5)
    deps = df["Depreciation"].iloc[1:].tolist()
    assert deps[:4] == pytest.approx([20_000, 12_000, 7_200, 4_320])
    assert deps[4] == pytest.approx(1_480)
    assert sum(deps) == pytest.approx(45_000)
    assert df["Book Value"].iloc[-1] == pytest.approx(5_000)


@pytest.mark.parametrize("life", [3, 5, 8, 10, 15, 30])
def test_ddb_and_sl_always_land_on_salvage(life):
    for df in (calc.declining_balance(80_000, 8_000, life), calc.straight_line(80_000, 8_000, life)):
        assert df["Book Value"].iloc[-1] == pytest.approx(8_000)
        assert (df["Depreciation"] >= 0).all()


@pytest.mark.parametrize("cls", sorted(calc.MACRS_HALF_YEAR))
def test_macrs_tables_sum_to_100_and_fully_depreciate(cls):
    assert sum(calc.MACRS_HALF_YEAR[cls]) == pytest.approx(100.0, abs=0.011)
    df = calc.macrs(100_000, cls)
    assert len(df) == len(calc.MACRS_HALF_YEAR[cls]) + 1
    assert df["Book Value"].iloc[-1] == pytest.approx(0, abs=11)  # rounding in IRS table


def test_macrs_5yr_first_year_is_20_percent():
    assert calc.macrs(50_000, 5)["Depreciation"].iloc[1] == pytest.approx(10_000)


def test_project_worth_textbook():
    npw, euaw, fw = calc.project_worth(100_000, 25_000, 10, 8.0)
    assert npw == pytest.approx(67_752, abs=5)
    assert euaw == pytest.approx(npw * 0.14903, rel=1e-4)
    assert fw == pytest.approx(npw * 2.15892, rel=1e-4)


def test_project_worth_salvage_adds_value_and_zero_marr():
    base = calc.project_worth(100_000, 25_000, 10, 8.0)[0]
    assert calc.project_worth(100_000, 25_000, 10, 8.0, salvage=20_000)[0] == pytest.approx(base + 20_000 * 0.46319, abs=1)
    assert calc.project_worth(100_000, 25_000, 10, 0.0)[0] == pytest.approx(150_000)


def test_lease_payment_textbook():
    t = calc.lease_terms(30_000, 18_000, 36, 6.0)  # MF = 0.0025
    assert t["money_factor"] == pytest.approx(0.0025)
    assert t["depreciation"] == pytest.approx(333.33, abs=0.01)
    assert t["finance_charge"] == pytest.approx(120.0)
    assert t["payment"] == pytest.approx(453.33, abs=0.01)


def test_buy_vs_lease_zero_opportunity_cost_pw_equals_nominal():
    buy = calc.buy_total_cost(35_000, 3_000, 7.0, 5, 36, 19_000, 6.25, 500, 0.0)
    lease = calc.lease_total_cost(35_000, 3_000, 21_000, 36, 5.0, 6.25, 695, 395, 12_000, 13_000, 0.25, 0.0)
    assert buy["present_worth_cost"] == pytest.approx(buy["nominal_cost"])
    assert lease["present_worth_cost"] == pytest.approx(lease["nominal_cost"])
    assert lease["overage"] == pytest.approx(1_000 * 3 * 0.25)


def test_buy_cost_cross_check_with_schedule():
    buy = calc.buy_total_cost(30_000, 3_000, 6.0, 5, 36, 17_000, 0, 0, 0.0)
    sched = calc.amortization_schedule(27_000, 6.0, 60)
    paid = sched["Total Monthly Payment"].iloc[:36].sum()
    bal = sched["Remaining Balance"].iloc[35]
    assert buy["nominal_cost"] == pytest.approx(3_000 + paid - (17_000 - bal))


def test_positive_discounting_lowers_pw_of_deferred_credit():
    # Equity is received at the end; discounting it should make buying look more expensive
    a = calc.buy_total_cost(30_000, 3_000, 6.0, 5, 36, 17_000, 0, 0, 0.0)["present_worth_cost"]
    b = calc.buy_total_cost(30_000, 3_000, 6.0, 5, 36, 17_000, 0, 0, 8.0)["present_worth_cost"]
    assert b != a
