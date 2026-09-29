# The Decision Engine

`flybot/decision/engine.py`

Two functions, `decide_entry()` and `decide_exit()`, hold every rule for
*when* FLYBOT acts on information the evaluator has already produced. This
module never looks at raw market data -- only `Score`, `Position`, and
price -- which is what keeps it simple enough to reason about exhaustively.

## Entry: BUY vs SKIP

```
if score.disqualified:            -> SKIP (hard filter reason)
elif score.confidence < buy_confidence_threshold:  -> SKIP (score too low)
else:                              -> BUY
```

A BUY decision also records:
- **conviction level** -- "strong" if confidence clears
  `strong_conviction_threshold`, otherwise "moderate"
- **top signal** -- whichever feature contributed the most to the score,
  surfaced in the log line so you can see *why* FLYBOT liked a pair, not
  just that it did

Note what's absent: the decision engine does not check whether there's
capital available, whether the position limit is already hit, or how big
to size the trade. A BUY here is "this pair clears the bar," not "we're
about to buy it" -- the risk manager (`flybot/risk/manager.py`) gets the
final say and can veto or resize.

## Exit: HOLD vs SELL

`decide_exit()` is checked against every open position, on every tick, in
this priority order:

1. **Take profit** -- `unrealized_pnl_pct >= take_profit_pct`
2. **Stop loss** -- `unrealized_pnl_pct <= stop_loss_pct`
3. **Trailing stop** -- only armed once a position has gained at least
   `trailing_stop_activate_pct`; after that, a drawdown from the position's
   peak price of `trailing_stop_pct` triggers an exit. This is what lets a
   big winner keep running instead of getting capped at the fixed
   take-profit, while still protecting most of the gain if it reverses.
4. **Time stop** -- `max_hold_seconds` exceeded, regardless of PnL. New-pair
   edges decay; a position that's neither hit its target nor been stopped
   out after 30 minutes (default) is more likely dead money than a future
   winner.
5. **Re-scan disqualification** -- on the slower re-evaluation cadence
   (`confidence_decay_check_seconds`), if a fresh snapshot would now trip a
   hard filter (e.g. liquidity has been pulled), FLYBOT exits immediately
   regardless of current PnL.
6. **Confidence decay** -- if a fresh score has fallen to less than half of
   the score at entry, FLYBOT treats that as the thesis breaking down and
   exits, even without a hard disqualification.

If none of the above trigger, the position is held.

## Why two re-evaluation speeds

Checking price is a single call and happens every tick. Checking hard
filters and confidence decay means pulling and scoring a fresh
`MarketSnapshot` -- more expensive, and in a real adapter, rate-limited.
`confidence_decay_check_seconds` controls how often that heavier check
runs, so FLYBOT can react to price instantly while only re-evaluating
fundamentals periodically.

## Worked example

```
Pair: DEGEN/SOL
Entry: confidence 0.74 (strong signal: momentum_score), size $120 @ $0.00469
  t+40s   price +18%     -> below trailing activation, below TP  -> HOLD
  t+95s   price +58%     -> trailing stop now armed (peak set)   -> HOLD
  t+110s  price +71%     -> new peak                              -> HOLD
  t+140s  price +52%     -> drawdown from peak = -11% (< 18%)     -> HOLD
  t+165s  price +48%     -> drawdown from peak = -13.5%           -> HOLD
  t+180s  price +41%     -> drawdown from peak = -17.5%           -> HOLD
  t+190s  price +38%     -> drawdown from peak = -19.3% (> 18%)   -> SELL (trailing_stop)
```

This is close to the actual behavior you'll see in a `run_demo.sh` run --
most winners exit via trailing stop, not the fixed take-profit, because
memecoin pumps are rarely smooth.
