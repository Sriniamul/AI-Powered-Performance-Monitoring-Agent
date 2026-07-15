import shutil
import subprocess
from typing import Dict


class JvmCollector:
    def __init__(self, config: dict):
        self.pid = config.get("pid")

    def collect(self) -> Dict:
        if not self.pid:
            return {"jvm_pid": None, "jvm_available": False}

        metrics = {"jvm_pid": self.pid, "jvm_available": True}
        metrics.update(self._heap_info())
        return metrics

    def _heap_info(self):
        if not shutil.which("jcmd"):
            return {"jvm_heap_info": "jcmd_not_found"}
        try:
            result = subprocess.run(
                ["jcmd", str(self.pid), "GC.heap_info"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return {
                "jvm_heap_info": result.stdout.strip()[-1000:] if result.stdout else "",
                "jvm_heap_info_error": result.stderr.strip()[-500:] if result.stderr else "",
            }
        except Exception as exc:
            return {"jvm_heap_info_error": str(exc)}
