"""Stress-test starting balances ignore actual balances dated in the future."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Account, ActualBalance, Base, User
from app.services import monte_carlo


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _add_balances(db, balances: dict[int, float]) -> User:
    user = User(name="Sample")
    account = Account(account_type="401k", user=user)
    for year, balance in balances.items():
        account.actual_balances.append(ActualBalance(year=year, balance=balance))
    db.add_all([user, account])
    db.commit()
    return user


def test_latest_actual_balance_skips_future_years(db):
    this_year = date.today().year
    user = _add_balances(db, {this_year - 1: 100.0, this_year: 120.0, this_year + 10: 9_999.0})

    assert monte_carlo._latest_actual_balance_for_account(db, user.id, "401k") == 120.0


def test_latest_actual_balance_is_none_when_only_future_years_exist(db):
    user = _add_balances(db, {date.today().year + 1: 500.0})

    assert monte_carlo._latest_actual_balance_for_account(db, user.id, "401k") is None
