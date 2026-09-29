# Risk Management

`flybot/risk/manager.py`

The decision engine answers "is this a good pair?" The risk manager
answers a completely different question: "even if it's good, can we
afford to take it right now?" It has veto power over every BUY, and it is
intentionally opinion-free about pair quality -- it doesn't know what a
memecoin is, only what the account's exposure and drawdown look like.

## Controls

| Control | Config key | Behavior |
|---|---|---|
| Max concurrent positions | `max_concurrent_positions` | Refuses new entries once N positions are open, regardless of confidence |
| Absolute position size cap | `max_position_size_usd` | Hard ceiling on any single position |
| Position size as % of equity | `max_position_pct_of_equity` | Scales position size down as equity shrinks, and up as it grows -- prevents a fixed dollar size from becoming an oversized bet after a drawdown |
| Daily loss circuit breaker | `max_daily_loss_pct` | Once realized+unrealized equity drops this much from the day's starting equity, **all new entries are refused for the rest of the day** |
| Max daily trades | `max_daily_trades` | Caps trade count regardless of PnL -- a safety valve against a misbehaving feed producing runaway churn |
| Loss-streak cooldown | `loss_streak_cooldown_trades`, `loss_streak_cooldown_seconds` | After N consecutive losing trades, stands down from new entries for a fixed cooldown window, on the theory that the current market regime may be one FLYBOT's model isn't suited for |

## Position sizing

```python
size = min(
    max_position_size_usd,
    equity_usd * max_position_pct_of_equity,
    equity_usd,   # can never size larger than available equity
)
```

All three caps are applied every time -- there's no mode where only one of
them is active. This means position size mechanically shrinks after
losses (protecting capital during a bad streak) and grows after wins (up
to the absolute cap), a form of implicit anti-martingale sizing.

## The circuit breaker is a one-way door within a day

Once `circuit_broken` is set, no further entries happen until
`RiskManager._maybe_roll_day()` resets state after 24 hours from the day's
start. This is deliberate: a circuit breaker that resets as soon as
drawdown ticks back under the threshold would let the system re-enter
during the same volatile conditions that tripped it in the first place.

## What the risk manager cannot protect against

- **Model risk.** If the scoring model is systematically wrong (e.g. it
  consistently rates a certain scam pattern highly), the risk manager will
  faithfully size and permit those trades right up until the daily loss
  limit trips. Risk controls limit *how much* damage a bad model can do
  per day, not whether the model is good.
- **Simulated market limits.** The bundled `SimulatedAdapter` does not
  model total liquidity depletion, so "size as % of equity" is the only
  thing preventing unrealistic position sizes relative to a thin pool in
  simulation. A real adapter should also cap position size relative to
  the pair's actual liquidity.
- **Correlated positions.** FLYBOT currently treats every open position as
  independent risk. If several open pairs are effectively correlated bets
  on the same narrative or the same few wallets, the position-count and
  sizing limits don't account for that concentration. This is a known
  simplification -- see the roadmap in the main README.
