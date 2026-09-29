"""
flybot.risk.manager
=======================

The risk manager is the only thing in FLYBOT with veto power over a BUY.
The decision engine can be as excited as it wants about a pair; if the
risk manager says no, the answer is no. This module intentionally contains
no "opinion" about whether a pair is good -- only about whether taking the
trade right now is something the account can survive.

Controls implemented:
  - max concurrent open positions
  - max size for a single position (absolute + % of equity)
  - daily loss circuit breaker (halts new entries for the rest of the day)
  - max trades per day (avoids runaway looping on a bad feed)
  - loss-streak cooldown (temporarily stands down after N losses in a row)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from flybot.core.config import RiskConfig


@dataclass
class RiskState:
    equity_usd: float
    day_start_equity_usd: float
    day_start_ts: float = field(default_factory=time.time)
    trades_today: int = 0
    consecutive_losses: int = 0
    cooldown_until: float = 0.0
    circuit_broken: bool = False


class RiskManager:
    def __init__(self, config: RiskConfig):
        self._config = config
        self.state = RiskState(
            equity_usd=config.starting_cash_usd,
            day_start_equity_usd=config.starting_cash_usd,
        )

    def _maybe_roll_day(self) -> None:
        if time.time() - self.state.day_start_ts > 86400:
            self.state.day_start_ts = time.time()
            self.state.day_start_equity_usd = self.state.equity_usd
            self.state.trades_today = 0
            self.state.circuit_broken = False

    def daily_drawdown_pct(self) -> float:
        if self.state.day_start_equity_usd == 0:
            return 0.0
        return (self.state.equity_usd - self.state.day_start_equity_usd) / self.state.day_start_equity_usd

    def can_open_new_position(self, open_position_count: int) -> tuple[bool, str]:
        self._maybe_roll_day()
        cfg = self._config

        if self.state.circuit_broken:
            return False, "daily loss circuit breaker tripped"

        if time.time() < self.state.cooldown_until:
            remaining = int(self.state.cooldown_until - time.time())
            return False, f"loss-streak cooldown active ({remaining}s remaining)"

        if open_position_count >= cfg.max_concurrent_positions:
            return False, f"max concurrent positions reached ({cfg.max_concurrent_positions})"

        if self.state.trades_today >= cfg.max_daily_trades:
            return False, f"max daily trades reached ({cfg.max_daily_trades})"

        if self.daily_drawdown_pct() <= -cfg.max_daily_loss_pct:
            self.state.circuit_broken = True
            return False, f"daily loss limit hit ({self.daily_drawdown_pct():.1%})"

        return True, "ok"

    def size_position(self) -> float:
        cfg = self._config
        pct_cap = self.state.equity_usd * cfg.max_position_pct_of_equity
        return max(0.0, min(cfg.max_position_size_usd, pct_cap, self.state.equity_usd))

    def record_trade_opened(self) -> None:
        self.state.trades_today += 1

    def record_trade_closed(self, realized_pnl_usd: float) -> None:
        self.state.equity_usd += realized_pnl_usd
        if realized_pnl_usd < 0:
            self.state.consecutive_losses += 1
            if self.state.consecutive_losses >= self._config.loss_streak_cooldown_trades:
                self.state.cooldown_until = time.time() + self._config.loss_streak_cooldown_seconds
        else:
            self.state.consecutive_losses = 0

        if self.daily_drawdown_pct() <= -self._config.max_daily_loss_pct:
            self.state.circuit_broken = True
