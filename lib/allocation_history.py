"""Dated 401(k) allocation history.

Each profile may define ``401k_allocation_history``: a list of entries shaped
as ``{"effective_date": "YYYY-MM-DD", "phases": {...}}``. An entry applies from
its effective date until the next entry takes effect. Changes are scheduled
for today or later, so historical compositions are never rewritten.

Profiles without a history fall back to their ``401k_phases`` as one entry.
The same mechanism serves the Roth IRA via ``ira_allocation_history`` and
``ira_phases`` (see ``ira_phases_for_year``).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from lib.phase_allocations import resolve_phase_allocation

DEFAULT_AGE_REFERENCE_YEAR = 2026
IRA_HISTORY_KEY = "ira_allocation_history"
IRA_LEGACY_KEY = "ira_phases"
_401K_HISTORY_KEY = "401k_allocation_history"
_401K_LEGACY_KEY = "401k_phases"
_LEGACY_EFFECTIVE_DATE = date(1900, 1, 1)
_PCT_TOLERANCE = 1e-6


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def get_history(
    profile: dict[str, Any],
    history_key: str = _401K_HISTORY_KEY,
    legacy_key: str = _401K_LEGACY_KEY,
) -> list[dict[str, Any]]:
    """Return history entries sorted by effective date, oldest first."""
    raw = profile.get(history_key)
    if not raw:
        return [{"effective_date": _LEGACY_EFFECTIVE_DATE.isoformat(), "phases": profile.get(legacy_key, {})}]
    return sorted(
        ({"effective_date": _parse_date(e["effective_date"]).isoformat(), "phases": e["phases"]} for e in raw),
        key=lambda e: e["effective_date"],
    )


def phases_on(
    profile: dict[str, Any],
    on: date,
    history_key: str = _401K_HISTORY_KEY,
    legacy_key: str = _401K_LEGACY_KEY,
) -> dict[str, Any]:
    """Return the phases in effect on ``on``.

    Dates before the first entry use the first entry so early history is not lost.
    """
    history = get_history(profile, history_key, legacy_key)
    chosen = history[0]
    for entry in history:
        if _parse_date(entry["effective_date"]) <= on:
            chosen = entry
    return chosen["phases"]


def phases_for_year(
    profile: dict[str, Any],
    year: int,
    today: date,
    history_key: str = _401K_HISTORY_KEY,
    legacy_key: str = _401K_LEGACY_KEY,
) -> dict[str, Any]:
    """Return the phases that govern contributions made during ``year``.

    The current calendar year uses the composition in effect today. Other years
    use the composition in effect on January 1 of that year.
    """
    if year == today.year:
        return phases_on(profile, today, history_key, legacy_key)
    return phases_on(profile, date(year, 1, 1), history_key, legacy_key)


def ira_phases_for_year(profile: dict[str, Any], year: int, today: date) -> dict[str, Any]:
    """Return the Roth IRA phases that govern contributions made during ``year``."""
    return phases_for_year(profile, year, today, IRA_HISTORY_KEY, IRA_LEGACY_KEY)


def age_to_year(profile: dict[str, Any], age: int) -> int:
    base_age = int(profile.get("age", 0))
    reference_year = int(profile.get("age_reference_year", DEFAULT_AGE_REFERENCE_YEAR))
    return reference_year + (age - base_age)


def allocation_for_year(profile: dict[str, Any], year: int, age: int, today: date) -> dict[str, dict[str, Any]]:
    """Return the resolved allocation (glide path applied) for ``age`` in ``year``."""
    return resolve_phase_allocation(phases_for_year(profile, year, today), age)


def validate_phases(phases: dict[str, Any]) -> None:
    """Raise ValueError if any phase allocation does not total 100%."""
    for key, phase in phases.items():
        allocation = phase.get("allocation")
        if not allocation:
            continue
        total = sum(float(cfg["pct"]) for cfg in allocation.values())
        if abs(total - 1.0) > _PCT_TOLERANCE:
            raise ValueError(f"{key} allocation totals {total:.6f}, expected 1.0")


def schedule_allocation_change(
    profile: dict[str, Any],
    effective_date: str | date,
    phases: dict[str, Any],
    today: date,
) -> list[dict[str, Any]]:
    """Return a new history with a future allocation change added.

    Entries dated before ``today`` are never modified. Scheduling a date that
    already has a future entry replaces that entry only.
    """
    effective = _parse_date(effective_date)
    if effective < today:
        raise ValueError("Allocation changes must take effect today or later")
    validate_phases(phases)

    history = get_history(profile)
    kept = [e for e in history if _parse_date(e["effective_date"]) != effective]
    kept.append({"effective_date": effective.isoformat(), "phases": phases})
    return sorted(kept, key=lambda e: e["effective_date"])
