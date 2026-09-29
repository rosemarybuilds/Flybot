"""
flybot.core.logging_utils
============================

A tiny, dependency-free "retro terminal" logger. No external UI framework --
just ANSI escape codes styled to match the FLYBOT black/yellow identity.
This is what produces the scrolling log you see in the README's simulated
boot sequence and in `python main.py` when you run it for real.
"""

from __future__ import annotations

import sys
import time

YELLOW = "\033[33m"
BOLD_YELLOW = "\033[1;33m"
RED = "\033[31m"
GREEN = "\033[32m"
DIM = "\033[2m"
RESET = "\033[0m"
BLINK = "\033[5m"


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _use_color() -> bool:
    return sys.stdout.isatty()


def _wrap(code: str, text: str) -> str:
    return f"{code}{text}{RESET}" if _use_color() else text


def scan(msg: str) -> None:
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(YELLOW, '[SCAN]')}   {msg}")


def eval_(msg: str) -> None:
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(BOLD_YELLOW, '[EVAL]')}   {msg}")


def decision(msg: str, action: str = "") -> None:
    color = GREEN if action == "BUY" else (RED if action == "SELL" else YELLOW)
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(color, '[DECIDE]')} {msg}")


def trade(msg: str, side: str = "buy") -> None:
    color = GREEN if side == "buy" else RED
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(color, '[TRADE]')}  {msg}")


def risk(msg: str) -> None:
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(RED, '[RISK]')}   {msg}")


def system(msg: str) -> None:
    print(f"{DIM}[{_ts()}]{RESET} {_wrap(DIM, '[SYS]')}    {msg}")


BANNER = r"""
   _____ _  __     ______  ____ _______
  |  ___| | \ \   / /  _ \/ __ \__   __|
  | |_  | |  \ \_/ /| |_) | |  | | | |
  |  _| | |   \   / |  _ <| |  | | | |
  | |   | |___| |  | |_) | |__| | | |
  |_|   |______|_|  |____/ \____/  |_|

        autonomous fly-brained trading experiment
        mode: SIMULATION -- no real funds, no real keys
"""


def print_banner() -> None:
    print(_wrap(BOLD_YELLOW, BANNER))
