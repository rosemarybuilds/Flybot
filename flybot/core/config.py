"""
flybot.core.config
====================

Loads config/config.example.yaml (or a user-supplied path) into typed,
dot-accessible dataclasses. Nothing in here ever reads a private key or
secret directly -- see flybot/adapters/README in docs/SIMULATION_VS_REAL.md
for how a real adapter would be wired up via environment variables.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ScannerConfig:
    poll_interval_ms: int = 750
    min_pair_age_seconds: int = 5
    max_pair_age_seconds: int = 600
    min_liquidity_usd: float = 2_500
    chains: list = field(default_factory=lambda: ["simulated"])
    dedupe_window_seconds: int = 3600


@dataclass
class EvaluationConfig:
    weights: dict = field(default_factory=lambda: {
        "liquidity_score": 0.20,
        "momentum_score": 0.25,
        "distribution_score": 0.20,
        "safety_score": 0.25,
        "activity_score": 0.10,
    })
    require_lp_lock_or_burn_pct: float = 60.0
    require_mint_authority_revoked: bool = True
    max_top10_holder_pct: float = 45.0
    max_dev_wallet_pct: float = 8.0


@dataclass
class DecisionConfig:
    buy_confidence_threshold: float = 0.62
    strong_conviction_threshold: float = 0.82
    cooldown_after_skip_seconds: int = 0
    take_profit_pct: float = 0.60
    stop_loss_pct: float = -0.22
    trailing_stop_pct: float = -0.18
    trailing_stop_activate_pct: float = 0.25
    max_hold_seconds: int = 1800
    confidence_decay_check_seconds: int = 120


@dataclass
class RiskConfig:
    starting_cash_usd: float = 1_000.0
    max_concurrent_positions: int = 5
    max_position_size_usd: float = 120.0
    max_position_pct_of_equity: float = 0.15
    max_daily_loss_pct: float = 0.20
    max_daily_trades: int = 60
    loss_streak_cooldown_trades: int = 3
    loss_streak_cooldown_seconds: int = 300


@dataclass
class ExecutionConfig:
    mode: str = "simulation"      # "simulation" is the only shipped mode
    slippage_bps: int = 80
    fee_bps: int = 30
    latency_ms: int = 150


@dataclass
class LoggingConfig:
    level: str = "INFO"
    style: str = "retro_terminal"
    log_dir: str = "logs"


@dataclass
class FlybotConfig:
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @staticmethod
    def _merge(dc, data: dict):
        if not data:
            return dc
        valid = {f.name for f in dataclasses.fields(dc)}
        return dataclasses.replace(dc, **{k: v for k, v in data.items() if k in valid})

    @classmethod
    def load(cls, path: str | Path) -> "FlybotConfig":
        raw: dict[str, Any] = yaml.safe_load(Path(path).read_text()) or {}
        cfg = cls()
        cfg.scanner = cls._merge(cfg.scanner, raw.get("scanner"))
        cfg.evaluation = cls._merge(cfg.evaluation, raw.get("evaluation"))
        cfg.decision = cls._merge(cfg.decision, raw.get("decision"))
        cfg.risk = cls._merge(cfg.risk, raw.get("risk"))
        cfg.execution = cls._merge(cfg.execution, raw.get("execution"))
        cfg.logging = cls._merge(cfg.logging, raw.get("logging"))
        return cfg
