# Configuration Reference

FLYBOT reads a single YAML file (default: `config/config.example.yaml`) into
the typed dataclasses in `flybot/core/config.py`. Copy the example, adjust,
and pass `--config path/to/yours.yaml` to `main.py`.

## `scanner`

| Key | Default | Meaning |
|---|---|---|
| `poll_interval_ms` | `750` | How often the scanner polls the adapter for new pairs |
| `min_pair_age_seconds` | `5` | Ignore pairs younger than this |
| `max_pair_age_seconds` | `600` | Stop considering a pair once it's older than this |
| `min_liquidity_usd` | `2500` | Reserved for adapter-side pre-filtering |
| `chains` | `["simulated"]` | Which `Chain` values the scanner accepts |
| `dedupe_window_seconds` | `3600` | How long a pair address is remembered to avoid reprocessing |

## `evaluation`

| Key | Default | Meaning |
|---|---|---|
| `weights.*` | see below | Per-feature weight in the confidence score (must reason sensibly if changed — see `docs/EVALUATION.md`) |
| `require_lp_lock_or_burn_pct` | `60.0` | Minimum LP lock-or-burn % to avoid disqualification |
| `require_mint_authority_revoked` | `true` | Disqualify if mint authority is still live |
| `max_top10_holder_pct` | `45.0` | Disqualify above this holder concentration |
| `max_dev_wallet_pct` | `8.0` | Disqualify above this dev wallet holding |

Default weights (must sum to a sensible total; they are not auto-normalized):

```yaml
liquidity_score:     0.20
momentum_score:      0.25
distribution_score:  0.20
safety_score:        0.25
activity_score:      0.10
```

## `decision`

| Key | Default | Meaning |
|---|---|---|
| `buy_confidence_threshold` | `0.62` | Minimum confidence to trigger a BUY |
| `strong_conviction_threshold` | `0.82` | Confidence above which a BUY is logged as "strong conviction" |
| `take_profit_pct` | `0.60` | Exit at +60% unrealized |
| `stop_loss_pct` | `-0.22` | Exit at -22% unrealized |
| `trailing_stop_pct` | `-0.18` | Exit if price gives back this much from its peak (once armed) |
| `trailing_stop_activate_pct` | `0.25` | Trailing stop only arms after this much unrealized gain |
| `max_hold_seconds` | `1800` | Hard time-based exit |
| `confidence_decay_check_seconds` | `120` | How often an open position gets a full re-evaluation (vs. just a price check) |

## `risk`

| Key | Default | Meaning |
|---|---|---|
| `starting_cash_usd` | `1000.0` | Simulated starting cash |
| `max_concurrent_positions` | `5` | Hard cap on open positions |
| `max_position_size_usd` | `120.0` | Absolute cap per position |
| `max_position_pct_of_equity` | `0.15` | Cap per position as a fraction of current equity |
| `max_daily_loss_pct` | `0.20` | Circuit breaker threshold (fraction of day-start equity) |
| `max_daily_trades` | `60` | Hard cap on trades per rolling day |
| `loss_streak_cooldown_trades` | `3` | Consecutive losses before a cooldown triggers |
| `loss_streak_cooldown_seconds` | `300` | Length of that cooldown |

## `execution`

| Key | Default | Meaning |
|---|---|---|
| `mode` | `simulation` | The only value implemented in this repository |
| `slippage_bps` | `80` | Reserved for adapters that model slippage explicitly |
| `fee_bps` | `30` | Reserved for adapters that model fees explicitly |
| `latency_ms` | `150` | Reserved for adapters that model execution latency |

## `logging`

| Key | Default | Meaning |
|---|---|---|
| `level` | `INFO` | Reserved for future log-level filtering |
| `style` | `retro_terminal` | Log formatting style (`flybot/core/logging_utils.py`) |
| `log_dir` | `logs` | Where a future file-logging option would write to |

## Overriding just what you need

`FlybotConfig.load()` merges your YAML on top of dataclass defaults field
by field, per section -- you only need to specify the keys you want to
change:

```yaml
# my-aggressive-config.yaml
decision:
  buy_confidence_threshold: 0.55
  take_profit_pct: 1.0
risk:
  max_position_size_usd: 40.0
  max_concurrent_positions: 8
```

```bash
python main.py --config my-aggressive-config.yaml --ticks 200 --seed 3
```
