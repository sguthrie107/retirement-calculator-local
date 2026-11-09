from datetime import date

import pytest

from lib.allocation_history import (
    allocation_for_year,
    get_history,
    ira_phases_for_year,
    phases_for_year,
    schedule_allocation_change,
    validate_phases,
)
from lib.ira import _ira_phase_allocation
from lib.phase_allocations import resolve_phase_allocation, resolve_phase_key

TODAY = date(2030, 11, 8)


def _phases(us_pct: float) -> dict:
    return {
        "phase_1": {
            "end_age": 50,
            "allocation": {
                "us_stock": {"pct": us_pct, "ticker": "X", "label": "S&P 500"},
                "foreign_stock": {"pct": round(1 - us_pct, 6), "ticker": "Y", "label": "Intl"},
            },
        },
        "phase_2": {
            "end_age": None,
            "allocation": {"us_stock": {"pct": 1.0, "ticker": "X", "label": "S&P 500"}},
        },
    }


def _profile() -> dict:
    return {
        "age": 30,
        "age_reference_year": 2026,
        "401k_allocation_history": [
            {"effective_date": "2028-01-01", "phases": _phases(0.65)},
            {"effective_date": "2030-11-08", "phases": _phases(0.60)},
        ],
    }


def test_legacy_profile_without_history_uses_401k_phases():
    profile = {"401k_phases": _phases(0.60)}
    history = get_history(profile)
    assert len(history) == 1
    assert history[0]["phases"] is profile["401k_phases"]


def test_past_year_uses_composition_in_effect_then():
    profile = _profile()
    assert phases_for_year(profile, 2029, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.65
    assert phases_for_year(profile, 2031, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.60


def test_current_year_uses_composition_in_effect_today():
    profile = _profile()
    assert phases_for_year(profile, 2030, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.60


def test_schedule_rejects_backdated_change():
    with pytest.raises(ValueError):
        schedule_allocation_change(_profile(), "2029-06-01", _phases(0.5), TODAY)


def test_schedule_leaves_historical_entries_unchanged():
    profile = _profile()
    updated = schedule_allocation_change(profile, "2032-01-01", _phases(0.40), TODAY)
    profile_after = {**profile, "401k_allocation_history": updated}

    assert phases_for_year(profile_after, 2029, TODAY) == phases_for_year(profile, 2029, TODAY)
    assert phases_for_year(profile_after, 2031, TODAY) == phases_for_year(profile, 2031, TODAY)
    assert phases_for_year(profile_after, 2032, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.40


def test_schedule_replaces_only_matching_future_entry():
    profile = _profile()
    updated = schedule_allocation_change(profile, "2030-11-08", _phases(0.50), TODAY)
    dates = [entry["effective_date"] for entry in updated]
    assert dates == ["2028-01-01", "2030-11-08"]
    assert updated[0]["phases"] == _profile()["401k_allocation_history"][0]["phases"]


def test_validate_rejects_allocation_not_totaling_100_percent():
    bad = {"phase_1": {"allocation": {"us_stock": {"pct": 0.9}, "bonds": {"pct": 0.05}}}}
    with pytest.raises(ValueError):
        validate_phases(bad)


def test_phase_without_start_age_begins_after_previous_phase():
    phases = {
        "phase_1": {"end_age": 29, "allocation": {}},
        "phase_2": {"end_age": None, "allocation": {}},
    }
    assert resolve_phase_key(phases, 29) == "phase_1"
    assert resolve_phase_key(phases, 30) == "phase_2"


def test_unbounded_phase_without_start_resolves_after_earlier_phases():
    phases = {
        "phase_1": {"end_age": 50, "allocation": {}},
        "phase_2": {"end_age": 65, "allocation": {}},
        "phase_3": {"end_age": None, "allocation": {}},
    }
    assert resolve_phase_key(phases, 52) == "phase_2"
    assert resolve_phase_key(phases, 70) == "phase_3"


def test_glide_path_applies_within_resolved_phase():
    phases = {
        "phase_1": {"end_age": 50, "allocation": {"us_stock": {"pct": 1.0}}},
        "phase_2": {
            "start_age": 51,
            "end_age": 65,
            "allocation": {},
            "glide_path": {
                "from_phase": "phase_1",
                "start_age": 51,
                "annual_bond_shift_pct": 0.02,
                "max_bond_pct": 0.20,
                "bond_fund": {"ticker": "B", "label": "Bonds"},
            },
        },
    }
    allocation = resolve_phase_allocation(phases, 56)
    assert allocation["bonds"]["pct"] == pytest.approx(0.10)
    assert allocation["us_stock"]["pct"] == pytest.approx(0.90)


def test_allocation_for_year_applies_glide_for_current_composition():
    profile = {"401k_phases": {"phase_1": {"end_age": None, "allocation": {"us_stock": {"pct": 1.0}}}}}
    allocation = allocation_for_year(profile, 2027, 40, TODAY)
    assert allocation["us_stock"]["pct"] == pytest.approx(1.0)


def test_framework_allocations_total_100_percent():
    phases = _phases(0.60)
    validate_phases(phases)


def test_current_401k_phases_can_mirror_latest_history_entry():
    profile = _profile()
    profile["401k_phases"] = get_history(profile)[-1]["phases"]
    assert profile["401k_phases"] == get_history(profile)[-1]["phases"]


def _ira_profile() -> dict:
    return {
        "age": 30,
        "age_reference_year": 2026,
        "ira_allocation_history": [
            {"effective_date": "1900-01-01", "phases": _phases(0.60)},
            {"effective_date": "2026-11-08", "phases": _phases(0.25)},
        ],
        "ira_phases": _phases(0.25),
    }


def test_ira_past_year_keeps_prior_mix():
    profile = _ira_profile()
    assert ira_phases_for_year(profile, 2025, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.60


def test_ira_current_and_future_years_use_new_mix():
    profile = _ira_profile()
    assert ira_phases_for_year(profile, 2030, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.25
    assert ira_phases_for_year(profile, 2031, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.25


def test_ira_legacy_profile_without_history_uses_ira_phases():
    profile = {"ira_phases": _phases(0.40)}
    assert ira_phases_for_year(profile, 2030, TODAY)["phase_1"]["allocation"]["us_stock"]["pct"] == 0.40


def test_ira_phase_allocation_resolves_per_year_for_each_phase():
    profile = _ira_profile()
    phase_1_2025 = _ira_phase_allocation(profile, "phase_1", 2025, 30, TODAY)
    phase_1_2027 = _ira_phase_allocation(profile, "phase_1", 2027, 30, TODAY)
    assert phase_1_2025["us_stock"]["pct"] == 0.60
    assert phase_1_2027["us_stock"]["pct"] == 0.25
