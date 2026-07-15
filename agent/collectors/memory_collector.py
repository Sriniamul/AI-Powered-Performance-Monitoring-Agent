import psutil


class MemoryCollector:
    def collect(self):
        vm = psutil.virtual_memory()
        return {
            "memory_percent": vm.percent,
            "memory_total_mb": round(vm.total / (1024 * 1024), 2),
            "memory_available_mb": round(vm.available / (1024 * 1024), 2),
            "memory_used_mb": round(vm.used / (1024 * 1024), 2),
        }
