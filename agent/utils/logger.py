import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logger(name: str):
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    return logging.getLogger(name)


def configure_logging(config: dict, log_name: str = "agent") -> Path:
    """Configure a bounded UTF-8 log file while retaining console output."""
    cfg = config.get("logging", {})
    log_dir = Path(cfg.get("directory", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{log_name}.log"
    max_bytes = max(1024, int(cfg.get("max_bytes", 5 * 1024 * 1024)))
    backup_count = max(1, int(cfg.get("backup_count", 5)))

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(cfg.get("level", "INFO")).upper(), logging.INFO))
    for handler in list(root.handlers):
        if getattr(handler, "_ai_perf_rotating_file", False):
            root.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler._ai_perf_rotating_file = True
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    return log_path
