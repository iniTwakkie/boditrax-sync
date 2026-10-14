"""Credential resolution and storage tests."""

from __future__ import annotations

import json
import stat

import pytest

from boditrax_sync.config import CredentialsError, load_credentials, save_credentials


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("BODITRAX_USERNAME", "BODITRAX_PASSWORD", "BODITRAX_CREDENTIALS"):
        monkeypatch.delenv(name, raising=False)


def test_env_credentials_win(tmp_path, monkeypatch) -> None:
    file = tmp_path / "credentials.json"
    file.write_text(json.dumps({"username": "file@x", "password": "file-pw"}))
    monkeypatch.setenv("BODITRAX_USERNAME", "env@x")
    monkeypatch.setenv("BODITRAX_PASSWORD", "env-pw")
    assert load_credentials(file) == ("env@x", "env-pw")


def test_load_from_file(tmp_path) -> None:
    file = tmp_path / "credentials.json"
    file.write_text(json.dumps({"username": "user@x", "password": "pw"}))
    assert load_credentials(file) == ("user@x", "pw")


def test_load_from_env_path(tmp_path) -> None:
    file = tmp_path / "alt.json"
    file.write_text(json.dumps({"username": "alt@x", "password": "alt-pw"}))
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BODITRAX_CREDENTIALS", str(file))
        assert load_credentials() == ("alt@x", "alt-pw")


def test_missing_credentials_raise(tmp_path) -> None:
    with pytest.raises(CredentialsError):
        load_credentials(tmp_path / "nope.json")


def test_save_sets_owner_only_permissions(tmp_path) -> None:
    file = save_credentials("user@x", "pw", tmp_path / "sub" / "credentials.json")
    saved = json.loads(file.read_text())
    assert saved == {"username": "user@x", "password": "pw"}
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
