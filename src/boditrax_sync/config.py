"""Credential loading and storage.

Resolution order for the account credentials:

1. ``BODITRAX_USERNAME`` / ``BODITRAX_PASSWORD`` environment variables
2. a credentials file (default ``~/.config/boditrax-sync/credentials.json``,
   overridable with ``BODITRAX_CREDENTIALS`` or ``--credentials``)
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _default_credentials_path() -> Path:
    config_dir = os.environ.get("BODITRAX_CONFIG_DIR")
    base = (
        Path(config_dir).expanduser()
        if config_dir
        else Path.home() / ".config" / "boditrax-sync"
    )
    return base / "credentials.json"


class CredentialsError(RuntimeError):
    """Raised when no usable Boditrax account credentials are available."""


def credentials_path(path: Path | None = None) -> Path:
    """Resolve the credentials file path: argument, then env, then default."""
    if path:
        return Path(path)
    from_env = os.environ.get("BODITRAX_CREDENTIALS")
    if from_env:
        return Path(from_env).expanduser()
    return _default_credentials_path()


def load_credentials(path: Path | None = None) -> tuple[str, str]:
    """Return (username, password) from the environment or the credentials file."""
    username = os.environ.get("BODITRAX_USERNAME")
    password = os.environ.get("BODITRAX_PASSWORD")
    if username and password:
        return username, password

    file = credentials_path(path)
    if file.is_file():
        data = json.loads(file.read_text(encoding="utf-8"))
        username = username or data.get("username")
        password = password or data.get("password")
        if username and password:
            return username, password

    raise CredentialsError(
        f"No Boditrax credentials found. Run `boditrax-sync login` to create {file}, "
        "or set BODITRAX_USERNAME and BODITRAX_PASSWORD."
    )


def save_credentials(username: str, password: str, path: Path | None = None) -> Path:
    """Write the credentials file with owner-only permissions."""
    file = credentials_path(path)
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    file.write_text(
        json.dumps({"username": username, "password": password}, indent=2) + "\n",
        encoding="utf-8",
    )
    file.chmod(0o600)
    return file
