"""
flybot.decision.engine
=========================

Two responsibilities live here, deliberately kept in one module because
they share the same vocabulary (Score, confidence, thresholds):

1. Entry decisions: given a Score for a newly scanned pair, choose
   BUY or SKIP.
2. Exit decisions: given an open Position and its current price/score,
   choose to SELL (and why) or HOLD.

The risk manager (flybot/risk/manager.py) has veto power over BUY decisions
made here -- this module answers "is this pair good?", not "can we afford
to take it right now?".
"""

from __future__ import annotations

import time

from flybot.core.config import DecisionConfig
from flybot.core.models import Action, Decision, ExitReason, Pair, Position, Score


def decide_entry(pair: Pair, score: Score, config: DecisionConfig) -> Decision:
    if score.disqualified:
        return Decision(
            action=Action.SKIP,
            pair=pair,
            score=score,
            reasoning=f"disqualified: {score.disqualify_reason}",
        )

    if score.confidence < config.buy_confidence_threshold:
        return Decision(
            action=Action.SKIP,
            pair=pair,
            score=score,
            reasoning=(
                f"confidence {score.confidence:.2f} below threshold "
                f"{config.buy_confidence_threshold:.2f}"
            ),
        )

    conviction = "strong" if score.confidence >= config.strong_conviction_threshold else "moderate"
    top_signal = max(score.components, key=score.components.get) if score.components else "n/a"
    return Decision(
        action=Action.BUY,
        pair=pair,
        score=score,
        reasoning=(
            f"{conviction} conviction (confidence {score.confidence:.2f}); "
            f"strongest signal: {top_signal}"
        ),
    )


def decide_exit(position: Position, current_price: float, current_score: Score | None,
                 config: DecisionConfig, now: float | None = None) -> tuple[bool, ExitReason | None, str]:
    """Returns (should_exit, reason, human_readable_explanation)."""
    now = now or time.time()
    pnl_pct = position.unrealized_pnl_pct(current_price)

    if current_price > position.peak_price:
        position.peak_price = current_price

    if pnl_pct >= config.take_profit_pct:
        return True, ExitReason.TAKE_PROFIT, f"+{pnl_pct:.0%} hit take-profit target"

    if pnl_pct <= config.stop_loss_pct:
        return True, ExitReason.STOP_LOSS, f"{pnl_pct:.0%} hit stop-loss floor"

    drawdown = position.drawdown_from_peak(current_price)
    peak_gain = position.unrealized_pnl_pct(position.peak_price)
    if peak_gain >= config.trailing_stop_activate_pct and drawdown <= config.trailing_stop_pct:
        return True, ExitReason.TRAILING_STOP, (
            f"gave back {drawdown:.0%} from peak (+{peak_gain:.0%}) -- trailing stop"
        )

    if position.hold_seconds(now) >= config.max_hold_seconds:
        return True, ExitReason.TIME_STOP, (
            f"held {position.hold_seconds(now):.0f}s, exceeds max hold "
            f"{config.max_hold_seconds}s"
        )

    if current_score is not None and current_score.disqualified:
        return True, ExitReason.LIQUIDITY_PULLED, (
            f"re-scan disqualified position: {current_score.disqualify_reason}"
        )

    if (current_score is not None and not current_score.disqualified
            and current_score.confidence < position.entry_score.confidence * 0.5):
        return True, ExitReason.CONFIDENCE_DECAY, (
            f"confidence decayed from {position.entry_score.confidence:.2f} "
            f"to {current_score.confidence:.2f}"
        )

    return False, None, "no exit condition met"
