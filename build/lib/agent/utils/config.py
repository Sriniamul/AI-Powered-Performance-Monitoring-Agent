from pathlib import Path
import yaml


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
