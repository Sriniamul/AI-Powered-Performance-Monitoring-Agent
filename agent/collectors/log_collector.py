from pathlib import Path
from datetime import datetime, timezone


class LogCollector:
    def __init__(self, config: dict):
        self.paths = [Path(p) for p in config.get("paths", [])]
        self.max_tail_lines = int(config.get("max_tail_lines", 300))

    def collect(self):
        collected = []
        out_dir = Path("artifacts") / "logs"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for path in self.paths:
            if not path.exists() or not path.is_file():
                continue
            lines = path.read_text(errors="ignore").splitlines()[-self.max_tail_lines:]
            out_file = out_dir / f"{path.name}.{stamp}.tail.log"
            out_file.write_text("\n".join(lines), encoding="utf-8")
            collected.append(str(out_file))
        return collected
