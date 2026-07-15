import argparse
import time
from dotenv import load_dotenv

from agent.agent_controller import AgentController
from agent.utils.config import load_config
from agent.utils.logger import get_logger

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
    controller = AgentController(config)

    if args.once:
        controller.run_cycle()
        return

    interval = int(config.get("agent", {}).get("poll_interval_seconds", 5))
    logger.info("Starting AI Performance Agent. Poll interval=%s seconds", interval)
    while True:
        controller.run_cycle()
        time.sleep(interval)


if __name__ == "__main__":
    main()
