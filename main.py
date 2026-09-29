#!/usr/bin/env python3
"""
FLYBOT entry point.

    python main.py --config config/config.example.yaml
    python main.py --config config/config.example.yaml --ticks 200   # bounded demo run

This always runs in simulation mode against flybot.adapters.simulated.SimulatedAdapter.
There is no code path in this repository that accepts or transmits a private
key. See docs/SIMULATION_VS_REAL.md before pointing this at anything real.
"""

from __future__ import annotations

import argparse
import time

from flybot.adapters.simulated import SimulatedAdapter
from flybot.core import logging_utils as log
from flybot.core.config import FlybotConfig
from flybot.execution.trader import Trader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FLYBOT in simulation mode.")
    parser.add_argument("--config", default="config/config.example.yaml")
    parser.add_argument("--ticks", type=int, default=0,
                         help="Run a bounded number of ticks instead of forever (0 = forever).")
    parser.add_argument("--seed", type=int, default=None,
                         help="Seed the simulated market for reproducible demo runs.")
    args = parser.parse_args()

    config = FlybotConfig.load(args.config)
    adapter = SimulatedAdapter(seed=args.seed)
    trader = Trader(adapter, config)

    if args.ticks <= 0:
        trader.run_forever()
        return

    log.print_banner()
    log.system(f"starting cash: ${trader.portfolio.cash_usd:,.2f} (simulation mode)")
    log.system(f"running {args.ticks} bounded ticks...")
    for _ in range(args.ticks):
        trader.tick()
        time.sleep(config.scanner.poll_interval_ms / 1000.0)

    log.system("run complete -- final summary:")
    summary = trader.portfolio.summary(trader._price_lookup)
    for k, v in summary.items():
        log.system(f"  {k}: {v}")


if __name__ == "__main__":
    main()
