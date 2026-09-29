# Lab Notes

Loose, dated notes from building FLYBOT. Kept because the reasoning behind
a decision is often more useful than the decision itself.

---

**On the trailing stop.** Early versions used a fixed take-profit only.
Backtesting against recorded simulation runs showed the fixed TP was
leaving a lot on the table on the pairs that kept running past +60% --
and also that a naive "never sell a winner" approach gave almost all of
it back on the ones that reversed hard. The trailing stop
(`trailing_stop_activate_pct` / `trailing_stop_pct`) is the compromise:
let a winner run, but only after it's proven it can run, and protect a
meaningful chunk of the peak once it has.

**On hard filters vs. weighted scoring.** The first version of the scorer
put "honeypot flag" in as just another weighted feature. That's wrong: a
honeypot means you cannot sell, full stop, and no amount of good momentum
or distribution offsets a trade you can't exit. Moved it (and three other
similarly binary conditions) into `hard_filter()` ahead of scoring
entirely. This is the single most important structural decision in the
evaluation stage.

**On why freshness is a multiplier, not a weight.** Originally
`freshness_score` was just a sixth weighted feature. The problem: a
9-minute-old pair with great fundamentals was scoring identically to a
9-minute-old pair with mediocre fundamentals but happened to also be
fresh -- freshness was masking real quality differences. Making it a
multiplier on the combined score fixes this: it discounts stale pairs
without letting "still fresh" substitute for "actually good."

**On the daily circuit breaker being one-way.** Tempting to let the
breaker reset as soon as equity recovers above the threshold intraday.
Deliberately didn't: if a bad session is bad because of the *market*
regime (not just bad luck), letting the breaker reset mid-session means
re-entering the same conditions that caused the drawdown. A full-day
stand-down forces the reset to correlate with an actual regime change,
not a lucky green candle.

**On position sizing being three caps applied together, not a mode
switch.** Originally had a "sizing mode" config option (fixed / % of
equity / kelly-ish). Replaced with all three constraints applied
simultaneously (`min()` of absolute cap, % of equity, and available
cash). Simpler to reason about, and it composes correctly on its own:
sizing shrinks during a drawdown and grows during a win streak without
needing separate logic for either case.

---

## Roadmap / open problems

Not implemented, and flagged here rather than silently glossed over:

- **Correlated position risk.** Every open position is currently treated
  as independent. A future risk layer should detect when multiple open
  positions are effectively the same bet (same narrative, same dev
  wallet cluster, same launch platform) and cap exposure to that cluster,
  not just to position count.
- **Slippage and partial fills.** The simulated adapter fills instantly
  at the current price. A more realistic simulator would model fill
  price as a function of position size relative to pool depth.
- **Backtest replay mode.** Right now the "market" is generated live and
  once. A recorded-snapshot replay mode would let changes to the scoring
  model or decision thresholds be evaluated against a fixed, reproducible
  dataset instead of a fresh random seed each time.
- **Multi-adapter fan-in.** The scanner currently assumes one adapter.
  Running against multiple chains/sources concurrently is architecturally
  supported (see `docs/SCANNER.md`) but not wired up in `main.py` yet.
