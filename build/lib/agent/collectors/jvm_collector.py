import re
import shutil
import subprocess
from typing import Dict


class JvmCollector:
    """Collects JVM heap, GC, thread, and class-loading telemetry."""

    def __init__(self, config: dict):
        self.configured_pid = config.get("pid")
        self.auto_discover = bool(config.get("auto_discover", True))

    def collect(self) -> Dict:
        pid = self.configured_pid or (self._discover_pid() if self.auto_discover else None)
        if not pid:
            return {"jvm_pid": None, "jvm_available": False, "jvm_status": "no_jvm_found"}
        metrics = {"jvm_pid": int(pid), "jvm_available": True, "jvm_status": "available"}
        metrics.update(self._gc_metrics(pid))
        metrics.update(self._class_metrics(pid))
        metrics.update(self._thread_metrics(pid))
        return metrics

    def _discover_pid(self):
        output = _run(["jcmd", "-l"])
        for line in output.splitlines():
            match = re.match(r"\s*(\d+)\s+(.+)", line)
            if match and "sun.tools.jcmd.JCmd" not in match.group(2):
                return int(match.group(1))
        return None

    def _gc_metrics(self, pid):
        output = _run(["jstat", "-gc", str(pid)])
        values = _parse_jstat(output)
        if not values:
            return {"jvm_gc_available": False}
        heap_capacity = sum(values.get(key, 0) for key in ("S0C", "S1C", "EC", "OC"))
        heap_used = sum(values.get(key, 0) for key in ("S0U", "S1U", "EU", "OU"))
        return {
            "jvm_gc_available": True,
            "jvm_heap_used_mb": round(heap_used / 1024, 2),
            "jvm_heap_capacity_mb": round(heap_capacity / 1024, 2),
            "jvm_heap_percent": round(heap_used / heap_capacity * 100, 1) if heap_capacity else 0,
            "jvm_young_gc_count": int(values.get("YGC", 0)),
            "jvm_young_gc_time_seconds": values.get("YGCT", 0),
            "jvm_full_gc_count": int(values.get("FGC", 0)),
            "jvm_full_gc_time_seconds": values.get("FGCT", 0),
            "jvm_gc_time_seconds": values.get("GCT", 0),
        }

    def _class_metrics(self, pid):
        values = _parse_jstat(_run(["jstat", "-class", str(pid)]))
        if not values:
            return {"jvm_class_loading_available": False}
        return {
            "jvm_class_loading_available": True,
            "jvm_classes_loaded": int(values.get("Loaded", 0)),
            "jvm_classes_unloaded": int(values.get("Unloaded", 0)),
            "jvm_class_load_time_seconds": values.get("Time", 0),
        }

    def _thread_metrics(self, pid):
        output = _run(["jcmd", str(pid), "Thread.print"])
        if not output:
            return {"jvm_threads_available": False}
        headers = [line for line in output.splitlines() if line.startswith('"')]
        return {
            "jvm_threads_available": True,
            "jvm_thread_count": len(headers),
            "jvm_daemon_thread_count": sum(" daemon " in f" {line.lower()} " for line in headers),
            "jvm_deadlock_detected": "found one java-level deadlock" in output.lower(),
        }


def _run(command: list[str]) -> str:
    if not shutil.which(command[0]):
        return ""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _parse_jstat(output: str) -> dict:
    lines = [line.split() for line in output.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return {}
    try:
        return {name: float(value) for name, value in zip(lines[0], lines[1])}
    except ValueError:
        return {}
