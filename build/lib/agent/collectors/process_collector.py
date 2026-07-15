import time

import psutil


class ProcessCollector:
    """Samples processes to provide best-effort resource attribution."""

    def collect(self, sample_seconds: float = 0.15):
        processes = []
        for process in psutil.process_iter(["pid", "name"]):
            try:
                name = process.info.get("name") or ""
                if process.pid == 0 or name.lower() == "system idle process":
                    continue
                process.cpu_percent(None)
                processes.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        time.sleep(sample_seconds)
        samples = []
        for process in processes:
            try:
                samples.append({
                    "pid": process.pid,
                    "name": process.name() or "unknown",
                    "cpu_percent": round(process.cpu_percent(None), 1),
                    "memory_percent": round(process.memory_percent(), 1),
                    "memory_mb": round(process.memory_info().rss / (1024 * 1024), 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return {
            "top_cpu_process": max(samples, key=lambda item: item["cpu_percent"], default=None),
            "top_memory_process": max(samples, key=lambda item: item["memory_percent"], default=None),
            "process_count": len(samples),
            "zombie_process_count": sum(1 for process in psutil.process_iter(["status"])
                                        if process.info.get("status") == psutil.STATUS_ZOMBIE),
        }
