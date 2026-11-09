"""
Interactive Retirement Projection Calculator (401k + IRA)

Prompts for current age, retirement age, and years to project past retirement,
then loads the rest of the plan (salary, contribution %, salary growth, fund
allocations, expected returns, withdrawal %) from the configured profile file so the
projection follows your actual configured strategy.

Usage:
    python calculate.py
"""

from datetime import date

import pandas as pd
from tabulate import tabulate

from lib.plan_by_age import retirement_401k_full_plan
from lib.ira import retirement_ira_full_plan
from lib.calculator_utils import load_user_profile, load_users_data
from lib import ui


def _resolve_company_match_pct(raw_match_pct: str) -> float:
    """Resolve a company match percentage to a decimal rate, or zero if invalid."""
    try:
        match_pct = float(raw_match_pct.rstrip("%").strip())
    except (AttributeError, ValueError):
        return 0.0

    if not 0.0 <= match_pct <= 10.0:
        return 0.0
    return match_pct / 100.0


def _build_yearly_table(
    df_401k: pd.DataFrame,
    df_ira: pd.DataFrame,
    retirement_age: int,
    withdrawal_pct: float,
    match_withdrawal_to_growth: bool = False,
) -> pd.DataFrame:
    """Merge 401k + IRA projections into one year-by-year table with growth % and withdrawals."""
    left = df_401k[["year", "age", "balance", "total_contribution", "growth"]].rename(
        columns={"total_contribution": "contribution_401k", "growth": "growth_401k"}
    )
    right = df_ira[["year", "age", "ira_balance", "ira_contribution", "growth"]].rename(
        columns={"growth": "growth_ira"}
    )

    merged = pd.merge(left, right, on=["year", "age"], how="outer").fillna(0)
    merged = merged.sort_values("year").reset_index(drop=True)

    merged["total_balance"] = merged["balance"] + merged["ira_balance"]
    merged["total_contribution"] = merged["contribution_401k"] + merged["ira_contribution"]
    merged["total_growth"] = merged["growth_401k"] + merged["growth_ira"]

    prior_balance = merged["total_balance"] - merged["total_growth"] - merged["total_contribution"]
    merged["growth_pct"] = merged["total_growth"] / prior_balance.replace(0, pd.NA) * 100
    merged["growth_pct"] = merged["growth_pct"].fillna(0)

    merged["withdrawal"] = 0.0
    merged["withdrawal_401k"] = 0.0
    merged["withdrawal_ira"] = 0.0
    retired_mask = merged["age"] >= retirement_age

    if match_withdrawal_to_growth:
        prior_year_growth = merged["total_growth"].shift(1).fillna(0.0)
        target_withdrawal = prior_year_growth.where(retired_mask, 0.0)
    else:
        target_withdrawal = merged.loc[retired_mask, "total_balance"] * withdrawal_pct
        target_withdrawal = target_withdrawal.reindex(merged.index, fill_value=0.0)

    # Draw from the 401k first, then the IRA for any remainder.
    from_401k = pd.concat([target_withdrawal, merged["balance"]], axis=1).min(axis=1)
    remaining = target_withdrawal - from_401k
    from_ira = pd.concat([remaining, merged["ira_balance"]], axis=1).min(axis=1)

    merged["withdrawal_401k"] = from_401k
    merged["withdrawal_ira"] = from_ira
    merged["withdrawal"] = merged["withdrawal_401k"] + merged["withdrawal_ira"]

    return merged


def _display_projection(merged: pd.DataFrame, beneficiary: str) -> None:
    if merged.empty:
        ui.print_error("No projection data — check age and retirement age inputs.")
        return

    display_data = []
    for _, row in merged.iterrows():
        display_data.append({
            "Year": int(row["year"]),
            "Age": int(row["age"]),
            "Total Balance": ui.format_currency(row["total_balance"]),
            "401k Balance": ui.format_currency(row["balance"]),
            "IRA Balance": ui.format_currency(row["ira_balance"]),
            "Contribution $": ui.format_currency(row["total_contribution"]),
            "401k Withdraw": ui.format_currency(row["withdrawal_401k"]),
            "IRA Withdraw": ui.format_currency(row["withdrawal_ira"]),
            "Withdrawal $": ui.format_currency(row["withdrawal"]),
            "Growth %": f"{row['growth_pct']:.2f}%",
        })

    start_age = int(merged["age"].iloc[0])
    end_age = int(merged["age"].iloc[-1])

    ui.print_data_panel(
        f"RETIREMENT PROJECTION: {beneficiary} (Ages {start_age} to {end_age})",
        tabulate(display_data, headers="keys", tablefmt="grid"),
    )

    final_balance = merged["total_balance"].iloc[-1]
    total_contributions = merged["total_contribution"].sum()
    total_withdrawals = merged["withdrawal"].sum()
    avg_growth_pct = merged.loc[merged["growth_pct"] != 0, "growth_pct"].mean()

    summary_data = [
        ["Final Combined Balance at Age " + str(end_age), ui.format_currency(final_balance)],
        ["Total Contributions", ui.format_currency(total_contributions)],
        ["Total Withdrawals Taken", ui.format_currency(total_withdrawals)],
        ["Average Annual Growth %", f"{avg_growth_pct:.2f}%"],
    ]
    ui.print_data_panel(
        "SUMMARY STATISTICS",
        tabulate(summary_data, tablefmt="plain", floatfmt=".2f"),
    )
    ui.print_divider()


def main() -> None:
    ui.print_header()
    current_year = date.today().year

    ui.print_section("PROFILE SELECTION")
    profiles = load_users_data().get("users", [])
    choices = {
        str(index): profile["name"]
        for index, profile in enumerate(profiles, start=1)
        if profile.get("name")
    }
    if not choices:
        raise ValueError("No user profiles are configured")
    name = ui.input_choice("Select a profile", choices)

    profile = load_user_profile(name)
    stored_age = int(profile["age"])
    stored_retirement_age = int(profile.get("retirement_age", 65))
    stored_withdrawal_pct = float(profile.get("withdrawal_pct") or 0.06)

    ui.print_section("PROJECTION PARAMETERS")
    age = ui.input_int("What is your current age?", default=stored_age)
    retirement_age = ui.input_int("What age do you plan to retire?", default=stored_retirement_age)
    post_retirement_years = ui.input_int(
        "How many years after retirement do you want to continue to calculate?", default=15
    )
    company_match_pct = _resolve_company_match_pct(
        ui.input_string("Company % Match?", default="0%")
    )
    match_withdrawal_to_growth = ui.input_string(
        "Match withdrawals to account growth in retirement? (y/n)", default="n"
    ).strip().lower().startswith("y")

    ui.print_divider()
    ui.print_status(f"Calculating projection for {name}...", "info")
    ui.print_divider()

    df_401k = retirement_401k_full_plan(
        name,
        current_year=current_year,
        post_retirement_years=post_retirement_years,
        match_pct_override=1.0,
        contribution_pct_override=0.08,
        contribution_schedule_override={
            "annual_contribution_pct_step_start_year": current_year + 1,
            "annual_contribution_pct_step_pct": 0.01,
            "annual_contribution_pct_step_cap_pct": 0.15,
            "company_match_pct": 1.0,
            "company_match_employee_cap_pct": company_match_pct,
        },
        age_override=age,
        retirement_age_override=retirement_age,
    )
    df_ira = retirement_ira_full_plan(
        name,
        current_year=current_year,
        post_retirement_years=post_retirement_years,
        age_override=age,
        retirement_age_override=retirement_age,
    )

    merged = _build_yearly_table(
        df_401k,
        df_ira,
        retirement_age,
        stored_withdrawal_pct,
        match_withdrawal_to_growth=match_withdrawal_to_growth,
    )
    _display_projection(merged, name)


if __name__ == "__main__":
    main()
