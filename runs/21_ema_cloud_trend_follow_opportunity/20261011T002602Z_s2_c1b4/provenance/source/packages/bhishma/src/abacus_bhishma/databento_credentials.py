"""Securely load the project's Databento API key from macOS Keychain."""

from __future__ import annotations

import getpass
import platform
import subprocess


KEYCHAIN_SERVICE = "abacus-bhishma.databento"
KEYCHAIN_LABEL = "Abacus Bhishma Databento API Key"


class DatabentoCredentialError(RuntimeError):
    """Raised when the Databento credential cannot be loaded safely."""


def _require_macos() -> None:
    if platform.system() != "Darwin":
        raise DatabentoCredentialError(
            "This project is configured to read Databento credentials from "
            "macOS Keychain."
        )


def store_interactively() -> None:
    """Create or update the Keychain entry using a hidden terminal prompt."""
    _require_macos()
    account = getpass.getuser()
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-a",
                account,
                "-s",
                KEYCHAIN_SERVICE,
                "-l",
                KEYCHAIN_LABEL,
                "-w",
            ],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DatabentoCredentialError(
            "Unable to store the Databento key in macOS Keychain."
        ) from exc


def load() -> str:
    """Return the API key without writing it to logs or project files."""
    _require_macos()
    account = getpass.getuser()
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DatabentoCredentialError(
            "Databento key not found. Run './scripts/databento setup-key' first."
        ) from exc

    api_key = result.stdout.strip()
    if len(api_key) != 32 or not api_key.startswith("db-"):
        raise DatabentoCredentialError(
            "The Keychain item exists but does not contain a valid Databento API key."
        )
    return api_key
