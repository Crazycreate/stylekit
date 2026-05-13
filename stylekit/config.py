"""Persistent user config — stored at ~/.config/stylekit/config.json.

Resolution order for any setting:
  1. Explicit CLI flag / function arg
  2. Environment variable (e.g. OPENROUTER_API_KEY)
  3. Project-local .env (auto-loaded)
  4. User config file (~/.config/stylekit/config.json)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def config_dir() -> Path:
    """Return platform-appropriate config dir, creating it if needed."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "stylekit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> Path:
    path = config_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # 权限收紧（仅类 Unix；Windows 由 ACL 默认管控）
    if sys.platform != "win32":
        path.chmod(0o600)
    return path


def get_api_key() -> str | None:
    """Try every source, return first non-empty key."""
    load_dotenv()  # 1. 项目 .env
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    cfg = load_config()
    return (cfg.get("api_key") or "").strip() or None


def get_setting(name: str, default=None):
    val = os.environ.get(f"STYLEKIT_{name.upper()}")
    if val:
        return val
    return load_config().get(name, default)
