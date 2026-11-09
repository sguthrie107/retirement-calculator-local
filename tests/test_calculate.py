import pytest

from calculate import _resolve_company_match_pct
from lib.plan_by_age import _project_phase


@pytest.mark.parametrize(
    ("raw_match_pct", "expected"),
    [
        ("", 0.0),
        ("5", 0.05),
        ("5%", 0.05),
        ("10%", 0.10),
        ("invalid", 0.0),
        ("-1%", 0.0),
        ("10.1%", 0.0),
    ],
)
def test_resolve_company_match_pct(raw_match_pct, expected):
    assert _resolve_company_match_pct(raw_match_pct) == pytest.approx(expected)


def test_company_match_percentage_adds_that_percentage_of_salary(monkeypatch):
    monkeypatch.setattr(
        "lib.plan_by_age._calculate_blended_yield_and_appreciation",
        lambda _allocation: (0.0, 0.0),
    )

    projection, _, _ = _project_phase(
        start_balance=0.0,
        start_age=40,
        end_age=41,
        start_year=2026,
        salary=100_000.0,
        contribution_pct=0.08,
        match_pct=1.0,
        salary_increase_pct=0.0,
        allocation={"stock": {"pct": 1.0, "ticker": "TEST"}},
        beneficiary="Test",
        phase_label="Test",
        contribution_details={"company_match_employee_cap_pct": 0.05},
    )

    assert projection.iloc[0]["employee_contribution"] == pytest.approx(8_000.0)
    assert projection.iloc[0]["employer_match"] == pytest.approx(5_000.0)
    assert projection.iloc[0]["total_contribution"] == pytest.approx(13_000.0)