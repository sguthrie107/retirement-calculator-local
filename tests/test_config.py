import pytest

from app.config import _normalize_database_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("postgres://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db"),
        ("postgresql://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db"),
        ("postgresql+psycopg2://user:pass@host/db", "postgresql+psycopg2://user:pass@host/db"),
        ("sqlite:///retirement.db", "sqlite:///retirement.db"),
    ],
)
def test_normalize_database_url_pins_psycopg2(monkeypatch, raw_url, expected):
    monkeypatch.setenv("DATABASE_URL", raw_url)
    assert _normalize_database_url("sqlite:///fallback.db") == expected


def test_normalize_database_url_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _normalize_database_url("sqlite:///retirement.db") == "sqlite:///retirement.db"
