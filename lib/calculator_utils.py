"""Shared utilities for the retirement calculator.

Centralises path resolution and users.json access so every service module
can import from one place instead of each defining its own copy.
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the project root directory (parent of the lib/ package)."""
    return Path(__file__).resolve().parent.parent


def _resolve_users_path() -> Path:
    configured_path = os.environ.get("RETIREMENT_USER_DATA_PATH")
    if configured_path:
        path = Path(configured_path.strip()).expanduser()
        return path if path.is_absolute() else project_root() / path

    local_path = project_root() / "data" / "users.local.json"
    if local_path.is_file():
        return local_path
    return project_root() / "data" / "users.json"


@functools.lru_cache(maxsize=4)
def _load_users_data_cached(users_path: str) -> dict[str, Any]:
    """Load and cache a user-profile file for the lifetime of the process."""
    path = Path(users_path)
    if not path.is_file():
        raise FileNotFoundError(f"User profile data file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_users_data() -> dict[str, Any]:
    """Return cached profiles from the configured user-data file.

    ``RETIREMENT_USER_DATA_PATH`` may be absolute or relative to the project
    root. Otherwise, a local ignored ``data/users.local.json`` takes precedence
    over the repository's ``data/users.json``.
    """
    return _load_users_data_cached(str(_resolve_users_path().resolve()))


def load_user_profile(username: str) -> dict[str, Any]:
    """Load a single user profile from the configured user-data file by name.

    Args:
        username: The user's name, e.g. ``'Steven'``.

    Returns:
        User profile dict.

    Raises:
        ValueError: If no user with the given name exists.
    """
    users_data = load_users_data()
    for user in users_data.get("users", []):
        if user.get("name") == username:
            return user
    raise ValueError(f"User '{username}' not found in configured profile data")


def compute_contribution_pct_for_year(
    contribution_details: dict[str, Any],
    calendar_year: int | None,
    *,
    base_pct_override: float | None = None,
    pct_boost: float = 0.0,
    cap_pct_override: float | None = None,
) -> float:
    """Return the effective employee 401k contribution rate for a calendar year.

    Supports an optional step-up schedule in ``contribution_details``:

    - ``annual_contribution_pct_step_start_year``
    - ``annual_contribution_pct_step_pct``
    - ``annual_contribution_pct_step_cap_pct``

    The configured ``start_year`` is the first year that receives the first step.
    Example: base 5%, start year 2031, step 1%, cap 15% → 2031 becomes 6%.
    """
    base_pct = (
        float(base_pct_override)
        if base_pct_override is not None
        else float(contribution_details.get("annual_contribution_pct", 0.0))
    )
    base_pct += float(pct_boost or 0.0)

    if calendar_year is None:
        return max(base_pct, 0.0)

    step_start_year = contribution_details.get("annual_contribution_pct_step_start_year")
    step_pct = float(contribution_details.get("annual_contribution_pct_step_pct", 0.0) or 0.0)
    cap_pct = (
        float(cap_pct_override)
        if cap_pct_override is not None
        else float(
            contribution_details.get("annual_contribution_pct_step_cap_pct", base_pct) or base_pct
        )
    )
    cap_pct += float(pct_boost or 0.0)

    if step_start_year is None or step_pct <= 0.0:
        return max(base_pct, 0.0)

    years_of_steps = max(0, int(calendar_year) - int(step_start_year) + 1)
    effective_pct = base_pct + (years_of_steps * step_pct)
    return max(0.0, min(effective_pct, cap_pct))
