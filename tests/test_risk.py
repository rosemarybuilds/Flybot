import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flybot.core.config import RiskConfig
from flybot.risk.manager import RiskManager


def test_position_sizing_respects_absolute_cap():
    config = RiskConfig(starting_cash_usd=10_000, max_position_size_usd=100,
                         max_position_pct_of_equity=0.5)
    risk = RiskManager(config)
    assert risk.size_position() == 100


def test_position_sizing_respects_pct_cap():
    config = RiskConfig(starting_cash_usd=200, max_position_size_usd=500,
                         max_position_pct_of_equity=0.10)
    risk = RiskManager(config)
    assert risk.size_position() == 20


def test_max_concurrent_positions_blocks_new_entries():
    config = RiskConfig(max_concurrent_positions=2)
    risk = RiskManager(config)
    allowed, _ = risk.can_open_new_position(open_position_count=2)
    assert not allowed


def test_daily_loss_circuit_breaker_trips():
    config = RiskConfig(starting_cash_usd=1000, max_daily_loss_pct=0.20)
    risk = RiskManager(config)
    risk.record_trade_closed(realized_pnl_usd=-250)
    allowed, reason = risk.can_open_new_position(open_position_count=0)
    assert not allowed
    assert "circuit breaker" in reason


def test_loss_streak_triggers_cooldown():
    config = RiskConfig(loss_streak_cooldown_trades=2, loss_streak_cooldown_seconds=60)
    risk = RiskManager(config)
    risk.record_trade_closed(realized_pnl_usd=-10)
    risk.record_trade_closed(realized_pnl_usd=-10)
    allowed, reason = risk.can_open_new_position(open_position_count=0)
    assert not allowed
    assert "cooldown" in reason


def test_win_resets_loss_streak():
    config = RiskConfig(loss_streak_cooldown_trades=2, loss_streak_cooldown_seconds=60)
    risk = RiskManager(config)
    risk.record_trade_closed(realized_pnl_usd=-10)
    risk.record_trade_closed(realized_pnl_usd=50)
    assert risk.state.consecutive_losses == 0
