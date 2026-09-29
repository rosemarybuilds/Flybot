"""
flybot.core.models
===================

Shared data structures that flow through the FLYBOT pipeline:

    RawPairEvent -> Pair -> MarketSnapshot -> FeatureVector -> Score -> Decision -> Position -> Trade

Every stage of the system consumes and/or produces one of these types. Keeping
them centralized (instead of passing dicts around) is what makes the scanner,
evaluator, decision engine, risk manager and executor independently testable.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Chain(str, Enum):
    SOLANA = "solana"
    BASE = "base"
    ETHEREUM = "ethereum"
    SIMULATED = "simulated"


class Action(str, Enum):
    BUY = "BUY"
    SKIP = "SKIP"
    HOLD = "HOLD"
    SELL = "SELL"


class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop"
    CONFIDENCE_DECAY = "confidence_decay"
    LIQUIDITY_PULLED = "liquidity_pulled"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class Pair:
    """A freshly detected tradable pair, as reported by an adapter."""

    address: str
    base_symbol: str
    quote_symbol: str
    chain: Chain
    created_at: float
    dex: str
    discovered_at: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.created_at)


@dataclass
class MarketSnapshot:
    """Point-in-time market/on-chain read for a pair. This is the raw material
    the evaluator turns into a FeatureVector. Fields are intentionally close
    to what a real indexer (e.g. a DEX aggregator or on-chain RPC) would give
    you, so a real adapter can populate this struct without touching anything
    downstream."""

    pair: Pair
    price_usd: float
    liquidity_usd: float
    fdv_usd: float
    volume_5m_usd: float
    buys_5m: int
    sells_5m: int
    holder_count: int
    top10_holder_pct: float
    lp_locked_pct: float
    lp_burned_pct: float
    mint_authority_revoked: bool
    freeze_authority_revoked: bool
    honeypot_flag: bool
    dev_wallet_pct: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class FeatureVector:
    """Normalized (roughly 0..1) features derived from a MarketSnapshot.
    This is what the scoring model actually looks at -- see
    flybot/evaluation/features.py for the transformation logic."""

    liquidity_score: float
    momentum_score: float
    distribution_score: float
    safety_score: float
    activity_score: float
    freshness_score: float
    raw: dict = field(default_factory=dict)


@dataclass
class Score:
    """Output of the scoring model for a single evaluation pass."""

    confidence: float           # 0..1 overall conviction
    components: dict            # per-feature contribution, for explainability
    disqualified: bool = False  # hard-filter tripped (honeypot, no LP lock, ...)
    disqualify_reason: Optional[str] = None


@dataclass
class Decision:
    """The action the decision engine has chosen, plus the reasoning trail."""

    action: Action
    pair: Pair
    score: Score
    reasoning: str
    size_usd: float = 0.0
    at: float = field(default_factory=time.time)


@dataclass
class Trade:
    """An executed (simulated or real) fill."""

    id: str
    pair: Pair
    side: str            # "buy" | "sell"
    price_usd: float
    size_usd: float
    quantity: float
    at: float = field(default_factory=time.time)
    exit_reason: Optional[ExitReason] = None


@dataclass
class Position:
    """An open (or closed) holding the trader is / was managing."""

    id: str
    pair: Pair
    entry_price: float
    quantity: float
    size_usd: float
    opened_at: float
    entry_score: Score
    peak_price: float = 0.0
    closed: bool = False
    closed_at: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    realized_pnl_usd: float = 0.0

    def __post_init__(self):
        if self.peak_price == 0.0:
            self.peak_price = self.entry_price

    def unrealized_pnl_usd(self, current_price: float) -> float:
        return (current_price - self.entry_price) * self.quantity

    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.entry_price == 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price

    def drawdown_from_peak(self, current_price: float) -> float:
        if self.peak_price == 0:
            return 0.0
        return (current_price - self.peak_price) / self.peak_price

    def hold_seconds(self, now: Optional[float] = None) -> float:
        end = self.closed_at if self.closed else (now or time.time())
        return max(0.0, end - self.opened_at)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
