"""Optional parity tests against the independently maintained numpy-financial package."""
import pytest

npf = pytest.importorskip("numpy_financial", reason="install .[verification] to run external benchmarks")

from lib import ira
from lib.plan_by_age import _project_phase


@pytest.mark.external_benchmark
def test_401k_midyear_contributions_match_equivalent_annuity(monkeypatch):
    annual_return = 0.065
    monkeypatch.setattr(
        "lib.plan_by_age._calculate_blended_yield_and_appreciation",
        lambda _allocation: (0.015, 0.05),
    )

    projection, _, _ = _project_phase(
        start_balance=25_000.0,
        start_age=40,
        end_age=43,
        start_year=2026,
        salary=100_000.0,
        contribution_pct=0.10,
        match_pct=0.0,
        salary_increase_pct=0.03,
        allocation={"stock": {"pct": 1.0, "ticker": "TEST"}},
        beneficiary="Benchmark",
        phase_label="Test",
    )

    expected_balance = 25_000.0
    salary = 100_000.0
    print("\n401(k) mid-year contribution benchmark")
    print("year  contribution  calculator balance  numpy-financial  difference")
    for row in projection.itertuples(index=False):
        contribution = salary * 0.10
        equivalent_end_of_year_payment = contribution * (1 + annual_return / 2)
        expected_balance = npf.fv(
            annual_return,
            1,
            -equivalent_end_of_year_payment,
            -expected_balance,
        )
        difference = row.balance - expected_balance
        print(
            f"{row.year}  ${contribution:>11,.2f}  ${row.balance:>16,.2f}  "
            f"${expected_balance:>15,.2f}  ${difference:>9,.4f}"
        )
        assert row.balance == pytest.approx(expected_balance, abs=0.01)
        salary *= 1.03


@pytest.mark.external_benchmark
def test_ira_beginning_of_year_contributions_match_annuity(monkeypatch):
    annual_return = 0.06
    monkeypatch.setattr(
        ira,
        "_calculate_blended_yield_and_appreciation",
        lambda _allocation: (0.01, 0.05),
    )
    monkeypatch.setattr(ira, "get_ira_contribution_limit", lambda _year: 7_500.0)

    projection, _ = ira._project_ira_phase(
        start_balance=15_000.0,
        start_age=40,
        end_age=43,
        start_year=2026,
        allocation={"stock": {"pct": 1.0, "ticker": "TEST"}},
        beneficiary="Benchmark",
        phase_label="Test",
    )

    expected_balance = 15_000.0
    print("\nIRA beginning-of-year contribution benchmark")
    print("year  contribution  calculator balance  numpy-financial  difference")
    for row in projection.itertuples(index=False):
        expected_balance = npf.fv(
            annual_return,
            1,
            -7_500.0,
            -expected_balance,
            when="begin",
        )
        difference = row.ira_balance - expected_balance
        print(
            f"{row.year}  ${7_500.0:>11,.2f}  ${row.ira_balance:>16,.2f}  "
            f"${expected_balance:>15,.2f}  ${difference:>9,.4f}"
        )
        assert row.ira_balance == pytest.approx(expected_balance, abs=0.01)