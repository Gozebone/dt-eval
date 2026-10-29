"""Tiny stdlib .env loader (no python-dotenv dependency).

Loads KEY=VALUE lines from <comparison root>/.env into os.environ without
overwriting keys already present in the environment (an exported variable wins,
so a CI shell can still override the file). Pure stdlib so it imports cleanly
under every method's virtualenv.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def load_env_file(path: Path | None = None) -> dict[str, str]:
    """Load KEY=VALUE lines from `path` (default <root>/.env) into os.environ.

    Skips blank lines and ``#`` comments. Values may be single/double quoted.
    Never overwrites an existing environment variable. Returns newly set keys.
    """
    p = Path(path) if path is not None else ENV_PATH
    if not p.exists():
        return {}
    added = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            added[key] = value
    return added
