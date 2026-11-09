import json

import pytest

from lib import calculator_utils


def _write_profiles(path, username):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"users": [{"name": username}]}), encoding="utf-8")


def test_local_profile_file_takes_precedence_without_environment_override(
    monkeypatch, tmp_path
):
    data_dir = tmp_path / "data"
    _write_profiles(data_dir / "users.json", "repository")
    _write_profiles(data_dir / "users.local.json", "local")
    monkeypatch.setattr(calculator_utils, "project_root", lambda: tmp_path)
    monkeypatch.delenv("RETIREMENT_USER_DATA_PATH", raising=False)

    assert calculator_utils.load_users_data()["users"][0]["name"] == "local"


def test_environment_path_overrides_local_profile_file(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    _write_profiles(data_dir / "users.local.json", "local")
    private_path = tmp_path / "private" / "profiles.json"
    _write_profiles(private_path, "configured")
    monkeypatch.setattr(calculator_utils, "project_root", lambda: tmp_path)
    monkeypatch.setenv("RETIREMENT_USER_DATA_PATH", str(private_path))

    assert calculator_utils.load_users_data()["users"][0]["name"] == "configured"


def test_missing_explicit_profile_path_fails_instead_of_falling_back(
    monkeypatch, tmp_path
):
    _write_profiles(tmp_path / "data" / "users.local.json", "local")
    monkeypatch.setattr(calculator_utils, "project_root", lambda: tmp_path)
    monkeypatch.setenv("RETIREMENT_USER_DATA_PATH", "private/missing.json")

    with pytest.raises(FileNotFoundError, match="User profile data file not found"):
        calculator_utils.load_users_data()


def test_load_user_profile_uses_configured_profile_file(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    _write_profiles(data_dir / "users.json", "repository")
    _write_profiles(data_dir / "users.local.json", "local")
    monkeypatch.setattr(calculator_utils, "project_root", lambda: tmp_path)
    monkeypatch.delenv("RETIREMENT_USER_DATA_PATH", raising=False)

    assert calculator_utils.load_user_profile("local") == {"name": "local"}
