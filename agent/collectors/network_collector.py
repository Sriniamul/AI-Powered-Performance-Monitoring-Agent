import time

import psutil


class NetworkCollector:
    def __init__(self):
        self._last = None

    def collect(self):
        counters = psutil.net_io_counters()
        now = time.monotonic()
        sent_rate = received_rate = 0.0
        if counters and self._last:
            previous_time, previous = self._last
            elapsed = max(now - previous_time, 0.001)
            sent_rate = max(counters.bytes_sent - previous.bytes_sent, 0) / elapsed / (1024 * 1024)
            received_rate = max(counters.bytes_recv - previous.bytes_recv, 0) / elapsed / (1024 * 1024)
        if counters:
            self._last = (now, counters)
        try:
            connections = len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, OSError):
            connections = None
        return {
            "network_sent_mb_s": round(sent_rate, 2),
            "network_received_mb_s": round(received_rate, 2),
            "network_connections": connections,
        }
