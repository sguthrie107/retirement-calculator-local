from datetime import date

import pytest

from app.services import benchmark, comparison, monte_carlo
from app.services.monte_carlo import AssetMoments
from lib import plan_by_age
from lib.allocation_history import allocation_for_year
from lib.plan_by_age import _allocation_resolver


TODAY = date(2030, 11, 8)


class FixedDate(date):
    @classmethod
    def today(cls):
        return TODAY


def _phases(x_pct: float) -> dict:
    return {
        "phase_1": {
            "end_age": None,
            "allocation": {
                "x_fund": {"pct": x_pct, "ticker": "X"},
                "y_fund": {"pct": round(1 - x_pct, 6), "ticker": "Y"},
            },
        }
    }


def _profile() -> dict:
    return {
        "age": 30,
        "age_reference_year": 2026,
        "current_401k_balance": 100_000,
        "current_ira_balance": 0,
        "401k_phases": _phases(0.60),
        "401k_allocation_history": [
            {"effective_date": "2025-01-01", "phases": _phases(0.70)},
            {"effective_date": "2030-11-08", "phases": _phases(0.60)},
            {"effective_date": "2032-01-01", "phases": _phases(0.40)},
        ],
    }


def test_deterministic_401k_resolver_uses_allocations_by_year(monkeypatch):
    monkeypatch.setattr(plan_by_age, "date", FixedDate)
    profile = _profile()
    resolve = _allocation_resolver(profile, start_year=2029, start_age=33)

    assert resolve(33)["x_fund"]["pct"] == pytest.approx(0.70)
    assert resolve(34)["x_fund"]["pct"] == pytest.approx(0.60)
    assert resolve(36)["x_fund"]["pct"] == pytest.approx(0.40)


def test_benchmark_uses_401k_composition_for_requested_year(monkeypatch):
    monkeypatch.setattr(benchmark, "date", FixedDate)
    profile = _profile()

    historical_weights = benchmark._user_proxy_weights(profile, 2029)
    current_weights = benchmark._user_proxy_weights(profile, 2030)
    future_weights = benchmark._user_proxy_weights(profile, 2033)

    assert historical_weights == {"X": 0.7, "Y": 0.3}
    assert current_weights == {"X": 0.6, "Y": 0.4}
    assert future_weights == {"X": 0.4, "Y": 0.6}


def test_monte_carlo_uses_401k_composition_for_each_simulated_year(monkeypatch):
    monkeypatch.setattr(monte_carlo, "date", FixedDate)
    profile = _profile()
    moments = {
        "X": AssetMoments(mean_return=0.10, volatility=0.10),
        "Y": AssetMoments(mean_return=0.20, volatility=0.20),
    }

    historical, _, = monte_carlo._account_phase_moments(
        profile, 33, moments, retirement_age=65, year=2029
    )
    current, _ = monte_carlo._account_phase_moments(
        profile, 34, moments, retirement_age=65, year=2030
    )
    future, _ = monte_carlo._account_phase_moments(
        profile, 37, moments, retirement_age=65, year=2033
    )

    assert historical[0] == pytest.approx(0.13)
    assert current[0] == pytest.approx(0.14)
    assert future[0] == pytest.approx(0.16)


def test_sequence_risk_uses_401k_composition_at_retirement(monkeypatch):
    monkeypatch.setattr(comparison, "date", FixedDate)
    monkeypatch.setattr(comparison, "_build_fund_moments", lambda: {})
    monkeypatch.setattr(
        comparison,
        "_rebalance_allocation_to_bond_target",
        lambda allocation: allocation,
    )
    monkeypatch.setattr(
        comparison,
        "_allocation_sequence_risk_returns",
        lambda allocation, _moments: [
            sum(
                fund["pct"]
                for fund in allocation.values()
                if fund["ticker"] == "X"
            )
        ],
    )

    returns = comparison._sequence_risk_returns_for_projected_portfolio(
        {
            **_profile(),
            "retirement_age": 37,
        },
        [{"year": 2033, "account_balances": {"401k": 100_000}}],
        current_year=2026,
        fund_moments={},
    )

    assert returns == pytest.approx([0.40])


def test_allocation_for_year_resolves_historical_and_future_entries():
    profile = _profile()

    assert allocation_for_year(profile, 2029, 33, TODAY)["x_fund"]["pct"] == pytest.approx(0.70)
    assert allocation_for_year(profile, 2030, 34, TODAY)["x_fund"]["pct"] == pytest.approx(0.60)
    assert allocation_for_year(profile, 2033, 37, TODAY)["x_fund"]["pct"] == pytest.approx(0.40)
