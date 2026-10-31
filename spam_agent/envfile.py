"""Minimal .env loader (no extra dependency). Real environment variables always win over the file."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path=None) -> list[str]:
    """Load KEY=VALUE lines from .env into os.environ without overriding existing variables. Returns the key names set.

    Set AGENTE_NO_DOTENV=1 to skip (the tests do, so a developer's real .env cannot change test behaviour)."""
    if os.environ.get("AGENTE_NO_DOTENV") == "1":
        return []
    p = Path(path) if path else ROOT / ".env"
    if not p.is_file():
        return []
    loaded = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if val[:1] in "\"'" and val.endswith(val[:1]) and len(val) >= 2:
            val = val[1:-1]
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        if key and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded
