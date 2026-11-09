"""Resolve configured phase allocations, including optional glide paths."""

from typing import Any


def _phase_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, str]:
    key, _ = item
    try:
        return int(key.rsplit("_", 1)[-1]), key
    except (ValueError, IndexError):
        return 999, key


def _phase_ranges(phases: dict[str, Any]) -> dict[str, tuple[int, int | None]]:
    """Map each phase key to its inclusive (start_age, end_age) range.

    A phase without ``start_age`` begins the year after the previous phase ends,
    so an unset start can no longer make a phase match every age.
    """
    ranges: dict[str, tuple[int, int | None]] = {}
    previous_end: int | None = None
    for key, phase in sorted(phases.items(), key=_phase_sort_key):
        end = None if phase.get("end_age") is None else int(phase["end_age"])
        if phase.get("start_age") is not None:
            start = int(phase["start_age"])
        else:
            start = 0 if previous_end is None else previous_end + 1
        ranges[key] = (start, end)
        previous_end = end
    return ranges


def resolve_phase_key(phases: dict[str, Any], age: int) -> str | None:
    """Return the key of the phase active at ``age``, or None if no phase applies."""
    ranges = _phase_ranges(phases)
    matching = [
        key
        for key, (start, end) in ranges.items()
        if age >= start and (end is None or age <= end)
    ]
    if not matching:
        return None
    return max(matching, key=lambda key: (ranges[key][0], key))


def resolve_phase_allocation(phases: dict[str, Any], age: int) -> dict[str, dict[str, Any]]:
    """Return the allocation active at ``age`` and apply its optional glide path."""
    phase_key = resolve_phase_key(phases, age)
    if phase_key is None:
        return {}

    phase = phases[phase_key]
    allocation = phase.get("allocation", {})
    glide = phase.get("glide_path")
    if not glide:
        return allocation

    source = phases.get(glide["from_phase"], {}).get("allocation", {})
    start_age = int(glide.get("start_age", _phase_ranges(phases)[phase_key][0]))
    bond_pct = min(
        float(glide.get("max_bond_pct", 1.0)),
        max(0, age - start_age) * float(glide.get("annual_bond_shift_pct", 0.0)),
    )
    result = {
        key: {**cfg, "pct": float(cfg["pct"]) * (1.0 - bond_pct)}
        for key, cfg in source.items()
    }
    bond_key = glide.get("bond_key", "bonds")
    result[bond_key] = {**glide["bond_fund"], "pct": bond_pct}
    return result