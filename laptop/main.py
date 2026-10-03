"""
ULTRON — Laptop Entry Point
Run: python main.py [--config laptop|uno_q] [--debug]
"""
import asyncio
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core.orchestrator import UltronOrchestrator
from core.ports        import PortBundle

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ultron.main")

def load_config(profile: str) -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    path = os.path.join(os.path.dirname(__file__), "config", f"{profile}.toml")
    with open(path, "rb") as f:
        return tomllib.load(f)

async def main(profile: str):
    logger.info(f"ULTRON starting — profile: {profile}")
    config = load_config(profile)
    ports  = await PortBundle.create(config)
    orch   = UltronOrchestrator(ports, config)
    try:
        await orch.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        await ports.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ULTRON AI Companion")
    parser.add_argument("--config", default="laptop", choices=["laptop","uno_q"])
    parser.add_argument("--debug",  action="store_true")
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(main(args.config))
