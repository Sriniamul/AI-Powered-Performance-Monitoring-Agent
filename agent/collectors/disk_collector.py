import time
from pathlib import Path

import psutil


class DiskCollector:
    def __init__(self, path: str = "."):
        self.path = str(Path(path).resolve().anchor or Path(path).resolve())
        self._last = None

    def collect(self):
        usage = psutil.disk_usage(self.path)
        counters = psutil.disk_io_counters()
        now = time.monotonic()
        read_rate = write_rate = 0.0
        if counters and self._last:
            previous_time, previous = self._last
            elapsed = max(now - previous_time, 0.001)
            read_rate = max(counters.read_bytes - previous.read_bytes, 0) / elapsed / (1024 * 1024)
            write_rate = max(counters.write_bytes - previous.write_bytes, 0) / elapsed / (1024 * 1024)
        if counters:
            self._last = (now, counters)
        return {
            "disk_percent": usage.percent,
            "disk_total_gb": round(usage.total / (1024 ** 3), 2),
            "disk_free_gb": round(usage.free / (1024 ** 3), 2),
            "disk_read_mb_s": round(read_rate, 2),
            "disk_write_mb_s": round(write_rate, 2),
        }
