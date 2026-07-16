import argparse
import time
from dotenv import load_dotenv

from agent.agent_controller import AgentController
from agent.utils.config import load_config
from agent.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="AI Performance Monitoring Agent")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to YAML config")
    parser.add_argument("--once", action="store_true", help="Run one monitoring cycle and exit")
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()
    config = load_config(args.config)
    configure_logging(config, "agent")
    if args.once:
        _run_configured_cycles(config)
        return

    interval = int(config.get("agent", {}).get("poll_interval_seconds", 5))
    logger.info("Starting AI Performance Agent. Poll interval=%s seconds", interval)
    while True:
        try:
            config = load_config(args.config)
            _run_configured_cycles(config)
        except Exception:
            logger.exception("Monitoring cycle failed")
        time.sleep(interval)


def _run_configured_cycles(config):
    machines = [m for m in config.get("machines", []) if m.get("enabled", True)]
    if not machines:
        return [AgentController(config).run_cycle()]
    results = []
    for machine in machines:
        try:
            results.append(AgentController(config, machine).run_cycle())
        except Exception as exc:
            logger.exception("Unable to monitor machine %s", machine.get("name") or machine.get("ip_address"))
            results.append({"status": "connection_error", "machine": machine.get("id"), "error": str(exc)})
    return results


if __name__ == "__main__":
    main()
