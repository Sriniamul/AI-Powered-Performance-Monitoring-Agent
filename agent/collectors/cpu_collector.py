import psutil


class CpuCollector:
    def collect(self):
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "cpu_count": psutil.cpu_count(logical=True),
            "load_avg": _safe_load_avg(),
        }


def _safe_load_avg():
    try:
        return psutil.getloadavg()
    except Exception:
        return None
