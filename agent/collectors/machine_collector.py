import platform
import socket


class MachineCollector:
    """Identifies the machine on which this agent process is deployed."""

    def collect(self):
        hostname = socket.gethostname() or platform.node() or "unknown-machine"
        return {
            "machine_name": hostname,
            "machine_ip": _resolve_ip(hostname),
            "operating_system": platform.system(),
            "os_release": platform.release(),
            "os_environment": _os_environment(),
            "architecture": platform.machine(),
        }


def _resolve_ip(hostname: str):
    try:
        return socket.gethostbyname(hostname)
    except OSError:
        return "unavailable"


def _os_environment():
    system = platform.system() or "Unknown OS"
    release = platform.release()
    if system == "Windows":
        edition = platform.win32_edition()
        prefix = "Windows Server" if "server" in edition.lower() else "Windows"
        return f"{prefix} {release}".strip()
    if system == "Linux":
        return "Linux"
    return f"{system} {release}".strip()
