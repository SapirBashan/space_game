#!/usr/bin/env python3
"""Launcher for the Simulated Radar TCP Server.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.config import default_config
from app.streaming.mock_server import MockRadarServer

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mock_server_launcher")


async def async_main():
    parser = argparse.ArgumentParser(description="Run Mock Radar TCP Streaming Server")
    parser.add_argument("--host", default=default_config.tcp_server_host, help="Bind IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=default_config.tcp_server_port, help="TCP Port (default: 8765)")
    parser.add_argument("--rate", type=float, default=1.0, help="Stream rate in frames/sec (default: 1.0)")
    parser.add_argument("--mode", default="AMP", choices=["AMP", "NOISE", "PHASE", "MIXED"], help="Data mode (default: AMP)")
    parser.add_argument("--clean", action="store_true", help="Disable simulated fault injections")
    parser.add_argument("--elements", type=int, default=256, help="Element count (default: 256)")
    parser.add_argument("--frequencies", type=int, default=64, help="Frequency channels count (default: 64)")
    args = parser.parse_args()

    server = MockRadarServer(
        host=args.host,
        port=args.port,
        streaming_rate_hz=args.rate,
        data_mode=args.mode,
        elements=args.elements,
        frequencies=args.frequencies,
        fault_injection_enabled=not args.clean,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Termination signal received. Shutting down server...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    print("===========================================================")
    print(f" Mock Radar TCP Server")
    print(f" Listening on: {args.host}:{args.port}")
    print(f" Rate: {args.rate} Hz | Mode: {args.mode} | Matrix: {args.elements}x{args.frequencies}")
    print(f" Fault Injections: {'Disabled (Clean)' if args.clean else 'Enabled'}")
    print(" Press Ctrl+C to terminate.")
    print("===========================================================")

    await server.start()
    try:
        await stop_event.wait()
    finally:
        await server.stop()


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
