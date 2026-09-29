"""
flybot.adapters.base
=======================

FLYBOT talks to the outside world through a single narrow interface. Every
concrete adapter (simulated or real) implements `MarketAdapter`. This is the
seam where a real integration (a DEX aggregator, an RPC node, a data
provider) would be plugged in -- nothing upstream of this file needs to
change to go from simulation to a real (read-only or execution-capable)
backend.

FLYBOT ships with exactly one adapter: `SimulatedAdapter`
(see flybot/adapters/simulated.py). There is no adapter in this repository
that holds, requests, or transmits private keys or trading credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from flybot.core.models import MarketSnapshot, Pair


class MarketAdapter(ABC):
    """Read/write boundary between FLYBOT and a market."""

    @abstractmethod
    def poll_new_pairs(self) -> Iterable[Pair]:
        """Return pairs created since the previous poll."""
        raise NotImplementedError

    @abstractmethod
    def get_snapshot(self, pair: Pair) -> MarketSnapshot:
        """Return the current market/on-chain read for a pair."""
        raise NotImplementedError

    @abstractmethod
    def get_price(self, pair: Pair) -> float:
        """Return the current mid price in USD for a pair."""
        raise NotImplementedError

    @abstractmethod
    def execute_buy(self, pair: Pair, size_usd: float) -> tuple[float, float]:
        """Execute (or simulate) a buy. Returns (fill_price, quantity)."""
        raise NotImplementedError

    @abstractmethod
    def execute_sell(self, pair: Pair, quantity: float) -> float:
        """Execute (or simulate) a sell. Returns fill_price."""
        raise NotImplementedError
