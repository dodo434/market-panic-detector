"""Use the platform credential vault for a complete, atomically stored key pair."""

import json
import os
import sys

SERVICE_NAME = "MarketPanicDetector"


def vault():
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring

        return WinVaultKeyring()
    from keyring.backends.SecretService import Keyring

    return Keyring()


def get_credentials() -> tuple[str | None, str | None]:
    env = (os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY"))
    if all(env):
        return env
    try:
        store = vault()
        pair = store.get_password(SERVICE_NAME, "iex-credentials")
        if pair:
            key, secret = json.loads(pair)
            return key, secret
        return store.get_password(SERVICE_NAME, "ALPACA_API_KEY"), store.get_password(
            SERVICE_NAME, "ALPACA_SECRET_KEY"
        )
    except Exception:
        # Locked or unavailable OS store goes through the same missing-keys screen.
        return None, None


def save_credentials(api_key: str, secret_key: str) -> None:
    pair = [api_key.strip(), secret_key.strip()]
    if not all(pair):
        raise ValueError("Enter both Alpaca credentials.")
    vault().set_password(SERVICE_NAME, "iex-credentials", json.dumps(pair))
