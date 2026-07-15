from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from agent.utils.logger import get_logger

logger = get_logger(__name__)


class ThreadDumpService:
    def __init__(self, config: dict):
        self.pid = config.get("pid")
        self.enabled = bool(config.get("thread_dump_enabled", True))

    def capture(self):
        if not self.enabled or not self.pid:
            logger.info("Thread dump skipped. enabled=%s pid=%s", self.enabled, self.pid)
            return []

        out_dir = Path("artifacts") / "dumps"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_file = out_dir / f"threaddump-{self.pid}-{stamp}.txt"

        commands = []
        if shutil.which("jcmd"):
            commands.append(["jcmd", str(self.pid), "Thread.print"])
        if shutil.which("jstack"):
            commands.append(["jstack", "-l", str(self.pid)])

        for cmd in commands:
            try:
                logger.info("Running thread dump command: %s", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
                if result.stdout:
                    out_file.write_text(result.stdout, encoding="utf-8", errors="ignore")
                    return [str(out_file)]
                logger.warning("Thread dump command produced no stdout. stderr=%s", result.stderr[-500:])
            except Exception as exc:
                logger.warning("Thread dump command failed: %s", exc)

        marker = out_dir / f"threaddump-skipped-{self.pid}-{stamp}.txt"
        marker.write_text("Thread dump could not be created. Check JDK tools and process permissions.\n", encoding="utf-8")
        return [str(marker)]
