from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from agent.utils.logger import get_logger

logger = get_logger(__name__)


class HeapDumpService:
    def __init__(self, config: dict):
        self.pid = config.get("pid")
        self.enabled = bool(config.get("heap_dump_enabled", True))

    def capture(self):
        if not self.enabled or not self.pid:
            logger.info("Heap dump skipped. enabled=%s pid=%s", self.enabled, self.pid)
            return []

        out_dir = Path("artifacts") / "dumps"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_file = out_dir / f"heapdump-{self.pid}-{stamp}.hprof"

        commands = []
        if shutil.which("jcmd"):
            commands.append(["jcmd", str(self.pid), "GC.heap_dump", str(out_file)])
        if shutil.which("jmap"):
            commands.append(["jmap", f"-dump:live,format=b,file={out_file}", str(self.pid)])

        for cmd in commands:
            try:
                logger.info("Running heap dump command: %s", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
                if out_file.exists() and out_file.stat().st_size > 0:
                    return [str(out_file)]
                logger.warning("Heap dump command did not create file. stderr=%s", result.stderr[-500:])
            except Exception as exc:
                logger.warning("Heap dump command failed: %s", exc)

        marker = out_dir / f"heapdump-skipped-{self.pid}-{stamp}.txt"
        marker.write_text("Heap dump could not be created. Check JDK tools and process permissions.\n", encoding="utf-8")
        return [str(marker)]
