"""
flybot.execution.portfolio
=============================

Tracks cash, open positions, and realized/unrealized PnL. This is the
"account state" that the UI panel in the screenshot (Portfolio / Cash /
Holdings / Realized / Unrealized) reads from directly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from flybot.adapters.base import MarketAdapter
from flybot.core.models import Decision, ExitReason, Position, Trade, new_id


@dataclass
class Portfolio:
    cash_usd: float
    positions: dict[str, Position] = field(default_factory=dict)
    closed_positions: list[Position] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    realized_pnl_usd: float = 0.0

    def equity(self, price_lookup) -> float:
        unreal = sum(
            p.quantity * price_lookup(p.pair) for p in self.positions.values()
        )
        return self.cash_usd + unreal

    def open_position(self, decision: Decision, adapter: MarketAdapter) -> Position:
        price, quantity = adapter.execute_buy(decision.pair, decision.size_usd)
        self.cash_usd -= decision.size_usd
        pos = Position(
            id=new_id("pos"),
            pair=decision.pair,
            entry_price=price,
            quantity=quantity,
            size_usd=decision.size_usd,
            opened_at=time.time(),
            entry_score=decision.score,
        )
        self.positions[pos.id] = pos
        self.trades.append(Trade(
            id=new_id("trade"), pair=decision.pair, side="buy",
            price_usd=price, size_usd=decision.size_usd, quantity=quantity,
        ))
        return pos

    def close_position(self, position: Position, adapter: MarketAdapter,
                        reason: ExitReason) -> Trade:
        price = adapter.execute_sell(position.pair, position.quantity)
        proceeds = price * position.quantity
        self.cash_usd += proceeds
        pnl = proceeds - position.size_usd
        position.closed = True
        position.closed_at = time.time()
        position.exit_price = price
        position.exit_reason = reason
        position.realized_pnl_usd = pnl
        self.realized_pnl_usd += pnl
        self.positions.pop(position.id, None)
        self.closed_positions.append(position)
        trade = Trade(
            id=new_id("trade"), pair=position.pair, side="sell",
            price_usd=price, size_usd=proceeds, quantity=position.quantity,
            exit_reason=reason,
        )
        self.trades.append(trade)
        return trade

    def summary(self, price_lookup) -> dict:
        unrealized = sum(
            p.unrealized_pnl_usd(price_lookup(p.pair)) for p in self.positions.values()
        )
        return {
            "cash_usd": round(self.cash_usd, 2),
            "holdings_count": len(self.positions),
            "equity_usd": round(self.equity(price_lookup), 2),
            "realized_pnl_usd": round(self.realized_pnl_usd, 2),
            "unrealized_pnl_usd": round(unrealized, 2),
        }
