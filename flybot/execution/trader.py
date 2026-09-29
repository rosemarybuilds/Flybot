"""
flybot.execution.trader
==========================

Trader wires every stage together into the actual loop:

    scan -> snapshot -> extract features -> score -> decide entry
         -> risk check -> execute -> monitor open positions -> decide exit

This is the closest thing FLYBOT has to a "brain stem" -- it doesn't
contain trading logic itself, it just calls the module that does, in
order, every tick.
"""

from __future__ import annotations

import time

from flybot.adapters.base import MarketAdapter
from flybot.core import logging_utils as log
from flybot.core.config import FlybotConfig
from flybot.core.models import Action, Pair
from flybot.decision.engine import decide_entry, decide_exit
from flybot.evaluation.features import extract_features
from flybot.evaluation.scorer import score_pair
from flybot.execution.portfolio import Portfolio
from flybot.risk.manager import RiskManager
from flybot.scanner.scanner import PairScanner


class Trader:
    def __init__(self, adapter: MarketAdapter, config: FlybotConfig):
        self.adapter = adapter
        self.config = config
        self.scanner = PairScanner(adapter, config.scanner)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio(cash_usd=config.risk.starting_cash_usd)
        self._last_exit_check: dict[str, float] = {}

    def _price_lookup(self, pair: Pair) -> float:
        return self.adapter.get_price(pair)

    def tick(self) -> None:
        self._scan_and_evaluate()
        self._monitor_positions()

    # -- new pair pipeline ------------------------------------------------

    def _scan_and_evaluate(self) -> None:
        fresh_pairs = self.scanner.scan()
        for pair in fresh_pairs:
            log.scan(f"new pair {pair.base_symbol}/{pair.quote_symbol} "
                      f"on {pair.dex} (age {pair.age_seconds:.1f}s)")
            self._evaluate_pair(pair)

    def _evaluate_pair(self, pair: Pair) -> None:
        snap = self.adapter.get_snapshot(pair)
        features = extract_features(snap)
        score = score_pair(snap, features, self.config.evaluation)

        if score.disqualified:
            log.eval_(f"{pair.base_symbol} disqualified -- {score.disqualify_reason}")
            return

        log.eval_(f"{pair.base_symbol} confidence={score.confidence:.2f} "
                  f"liq=${snap.liquidity_usd:,.0f}")

        decision = decide_entry(pair, score, self.config.decision)
        log.decision(f"{pair.base_symbol}: {decision.action.value} -- {decision.reasoning}",
                     action=decision.action.value)

        if decision.action != Action.BUY:
            return

        allowed, why = self.risk.can_open_new_position(len(self.portfolio.positions))
        if not allowed:
            log.risk(f"veto BUY {pair.base_symbol} -- {why}")
            return

        decision.size_usd = self.risk.size_position()
        if decision.size_usd <= 0:
            log.risk(f"veto BUY {pair.base_symbol} -- no capital available")
            return

        position = self.portfolio.open_position(decision, self.adapter)
        self.risk.record_trade_opened()
        log.trade(
            f"BOUGHT {pair.base_symbol} @ ${position.entry_price:.8f} "
            f"size=${decision.size_usd:.2f}", side="buy",
        )

    # -- position monitoring ------------------------------------------------

    def _monitor_positions(self) -> None:
        for pos in list(self.portfolio.positions.values()):
            price = self.adapter.get_price(pos.pair)

            current_score = None
            interval = self.config.decision.confidence_decay_check_seconds
            if time.time() - self._last_exit_check.get(pos.id, 0) >= interval:
                snap = self.adapter.get_snapshot(pos.pair)
                features = extract_features(snap)
                current_score = score_pair(snap, features, self.config.evaluation)
                self._last_exit_check[pos.id] = time.time()

            should_exit, reason, why = decide_exit(pos, price, current_score, self.config.decision)
            if not should_exit:
                continue

            trade = self.portfolio.close_position(pos, self.adapter, reason)
            self.risk.record_trade_closed(pos.realized_pnl_usd)
            side = "sell"
            pnl_pct = (trade.price_usd - pos.entry_price) / pos.entry_price
            log.trade(
                f"SOLD {pos.pair.base_symbol} @ ${trade.price_usd:.8f} "
                f"pnl=${pos.realized_pnl_usd:+.2f} ({pnl_pct:+.1%}) -- {why}",
                side=side,
            )

    def run_forever(self) -> None:
        log.print_banner()
        log.system(f"starting cash: ${self.portfolio.cash_usd:,.2f} (simulation mode)")
        try:
            while True:
                self.tick()
                time.sleep(self.config.scanner.poll_interval_ms / 1000.0)
        except KeyboardInterrupt:
            log.system("shutdown requested -- final summary:")
            summary = self.portfolio.summary(self._price_lookup)
            for k, v in summary.items():
                log.system(f"  {k}: {v}")
