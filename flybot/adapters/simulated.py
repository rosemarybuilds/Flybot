"""
flybot.adapters.simulated
============================

SimulatedAdapter fabricates a plausible stream of "new pair" events and
attaches a self-consistent, semi-random on-chain profile to each one, then
evolves each pair's price with a bounded random walk. It is the only
adapter shipped in this repository.

Explicitly NOT real:
  - no network calls
  - no wallets, keys, or signing
  - no connection to any DEX, RPC, or aggregator
  - "honeypot", "LP lock" etc. flags are randomly generated, not read on-chain

This exists so the rest of the pipeline (scanner -> evaluator -> decision
engine -> risk manager -> executor) can be fully exercised end-to-end
without any external dependency. See docs/SIMULATION_VS_REAL.md for the
adapter contract a real integration would need to satisfy.
"""

from __future__ import annotations

import random
import string
import time
from dataclasses import dataclass

from flybot.adapters.base import MarketAdapter
from flybot.core.models import Chain, MarketSnapshot, Pair

_SYLLABLES = ["POP", "MOG", "WIF", "BONK", "PEPE", "FROG", "CAT", "GIGA",
              "TURBO", "SIGMA", "BASED", "MOON", "RIZZ", "SNIPE", "FLY",
              "GLITCH", "NANO", "PUMP", "DEGEN", "ORB"]


def _random_symbol() -> str:
    return random.choice(_SYLLABLES) + random.choice(["", str(random.randint(2, 999))])


def _random_addr() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=32))


@dataclass
class _SimState:
    price: float
    liquidity: float
    fdv: float
    holder_count: int
    top10_holder_pct: float
    lp_locked_pct: float
    lp_burned_pct: float
    mint_authority_revoked: bool
    freeze_authority_revoked: bool
    honeypot_flag: bool
    dev_wallet_pct: float
    drift: float
    vol: float


class SimulatedAdapter(MarketAdapter):
    def __init__(self, seed: int | None = None, spawn_rate_per_poll: float = 0.35):
        self._rng = random.Random(seed)
        self._spawn_rate = spawn_rate_per_poll
        self._state: dict[str, _SimState] = {}
        self._pairs: dict[str, Pair] = {}

    # -- discovery -----------------------------------------------------

    def poll_new_pairs(self):
        new_pairs = []
        if self._rng.random() < self._spawn_rate:
            pair = self._spawn_pair()
            new_pairs.append(pair)
        return new_pairs

    def _spawn_pair(self) -> Pair:
        addr = _random_addr()
        pair = Pair(
            address=addr,
            base_symbol=_random_symbol(),
            quote_symbol="SOL",
            chain=Chain.SIMULATED,
            created_at=time.time() - self._rng.uniform(0, 8),
            dex=self._rng.choice(["raydium-sim", "meteora-sim", "orca-sim"]),
        )
        self._pairs[addr] = pair

        # archetype mix: mostly junk, occasionally a clean-looking mover
        archetype = self._rng.choices(
            ["junk", "mid", "clean_mover", "rug_setup"],
            weights=[0.45, 0.30, 0.15, 0.10],
        )[0]

        if archetype == "clean_mover":
            liq = self._rng.uniform(15_000, 90_000)
            top10 = self._rng.uniform(8, 28)
            lp_lock = self._rng.uniform(70, 100)
            mint_rv = True
            freeze_rv = True
            honeypot = False
            dev_pct = self._rng.uniform(0, 4)
            drift = self._rng.uniform(0.02, 0.09)
            vol = self._rng.uniform(0.02, 0.05)
        elif archetype == "mid":
            liq = self._rng.uniform(4_000, 20_000)
            top10 = self._rng.uniform(20, 45)
            lp_lock = self._rng.uniform(30, 80)
            mint_rv = self._rng.random() < 0.6
            freeze_rv = self._rng.random() < 0.6
            honeypot = self._rng.random() < 0.05
            dev_pct = self._rng.uniform(2, 9)
            drift = self._rng.uniform(-0.02, 0.04)
            vol = self._rng.uniform(0.03, 0.07)
        elif archetype == "rug_setup":
            liq = self._rng.uniform(3_000, 12_000)
            top10 = self._rng.uniform(45, 85)
            lp_lock = self._rng.uniform(0, 25)
            mint_rv = False
            freeze_rv = self._rng.random() < 0.3
            honeypot = self._rng.random() < 0.35
            dev_pct = self._rng.uniform(10, 35)
            drift = self._rng.uniform(0.05, 0.20)   # tempting pump before the dump
            vol = self._rng.uniform(0.05, 0.12)
        else:  # junk
            liq = self._rng.uniform(500, 5_000)
            top10 = self._rng.uniform(30, 70)
            lp_lock = self._rng.uniform(0, 50)
            mint_rv = self._rng.random() < 0.3
            freeze_rv = self._rng.random() < 0.3
            honeypot = self._rng.random() < 0.15
            dev_pct = self._rng.uniform(5, 25)
            drift = self._rng.uniform(-0.06, 0.02)
            vol = self._rng.uniform(0.04, 0.10)

        price = self._rng.uniform(0.0000001, 0.01)
        self._state[addr] = _SimState(
            price=price,
            liquidity=liq,
            fdv=price * self._rng.uniform(5e8, 5e10),
            holder_count=self._rng.randint(5, 400),
            top10_holder_pct=top10,
            lp_locked_pct=lp_lock,
            lp_burned_pct=max(0.0, lp_lock - self._rng.uniform(0, 20)),
            mint_authority_revoked=mint_rv,
            freeze_authority_revoked=freeze_rv,
            honeypot_flag=honeypot,
            dev_wallet_pct=dev_pct,
            drift=drift,
            vol=vol,
        )
        return pair

    # -- market data -----------------------------------------------------

    def _step(self, addr: str) -> None:
        st = self._state[addr]
        shock = self._rng.gauss(st.drift, st.vol)
        st.price = max(1e-12, st.price * (1 + shock))
        st.liquidity = max(0.0, st.liquidity * (1 + self._rng.gauss(0, 0.03)))
        st.fdv = st.price * self._rng.uniform(5e8, 5e10)

    def get_snapshot(self, pair: Pair) -> MarketSnapshot:
        self._step(pair.address)
        st = self._state[pair.address]
        buys = self._rng.randint(0, 40)
        sells = self._rng.randint(0, 40)
        return MarketSnapshot(
            pair=pair,
            price_usd=st.price,
            liquidity_usd=st.liquidity,
            fdv_usd=st.fdv,
            volume_5m_usd=st.liquidity * self._rng.uniform(0.05, 1.4),
            buys_5m=buys,
            sells_5m=sells,
            holder_count=st.holder_count,
            top10_holder_pct=st.top10_holder_pct,
            lp_locked_pct=st.lp_locked_pct,
            lp_burned_pct=st.lp_burned_pct,
            mint_authority_revoked=st.mint_authority_revoked,
            freeze_authority_revoked=st.freeze_authority_revoked,
            honeypot_flag=st.honeypot_flag,
            dev_wallet_pct=st.dev_wallet_pct,
        )

    def get_price(self, pair: Pair) -> float:
        self._step(pair.address)
        return self._state[pair.address].price

    # -- execution (simulated fills only) --------------------------------

    def execute_buy(self, pair: Pair, size_usd: float):
        price = self.get_price(pair)
        quantity = size_usd / price
        return price, quantity

    def execute_sell(self, pair: Pair, quantity: float) -> float:
        price = self.get_price(pair)
        return price
