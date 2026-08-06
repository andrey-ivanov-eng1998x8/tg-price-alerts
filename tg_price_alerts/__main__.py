import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from tg_price_alerts import setup_logging
from tg_price_alerts.config import load_config
from tg_price_alerts.engine import AlertEngine

log = logging.getLogger("tg_price_alerts")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Poll price tickers and push alerts to Telegram")
    p.add_argument("-c", "--config", default="config.yaml", help="Path to yaml config file")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    p.add_argument("--test-config", action="store_true", help="Validate config syntax and exit")
    return p.parse_args(argv)


async def amain(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)

    config_file = Path(args.config)
    if not config_file.exists():
        log.error("config file not found: %s", config_file)
        return 1

    try:
        cfg = load_config(config_file)
    except Exception as e:
        log.error("invalid configuration: %s", e)
        return 1

    if args.test_config:
        watchers_count = len(cfg.watchers)
        rules_count = sum(len(w.targets) for w in cfg.watchers)
        log.info("config OK: %d watchers, %d total alert rules loaded", watchers_count, rules_count)
        return 0

    engine = AlertEngine(cfg)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_signal():
        log.info("received termination signal, shutting down...")
        stop_event.set()
        engine.stop()

    # windows does not support add_signal_handler properly
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _on_signal)

    try:
        await engine.run(stop_event=stop_event)
    except asyncio.CancelledError:
        pass
    finally:
        await engine.cleanup()

    return 0


def main() -> None:
    args = parse_args()
    try:
        code = asyncio.run(amain(args))
        sys.exit(code)
    except KeyboardInterrupt:
        # print("DEBUG: forced exit")
        sys.exit(0)


if __name__ == "__main__":
    main()
