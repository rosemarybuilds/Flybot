# What's Real vs. What's Simulated

This document exists because it should be impossible to misread this
repository as connecting to real markets or moving real funds. It doesn't.

## Simulated (this is everything in the shipped repo)

| Thing | Where | What that means |
|---|---|---|
| New pair discovery | `flybot/adapters/simulated.py::poll_new_pairs` | Pairs are fabricated on a random schedule with a random archetype mix (junk / mid / clean mover / rug setup) — nothing is read from any real chain |
| Prices | `SimulatedAdapter._step` | A bounded Gaussian random walk per pair, parameterized by its archetype | 
| On-chain safety flags | `SimulatedAdapter._spawn_pair` | LP lock %, mint/freeze authority, honeypot flag, holder concentration are all randomly generated per archetype, not read from any indexer |
| Order execution | `SimulatedAdapter.execute_buy/execute_sell` | Fills happen instantly at the current simulated price; no slippage, partial fills, MEV, or failed transactions are modeled yet |
| Wallets / keys | nowhere | There is no code path in this repository that reads, stores, or transmits a private key or seed phrase |

## Real (and reusable regardless of data source)

Everything **above** the adapter boundary is real, working logic that
operates identically whether the data behind it is simulated or genuine:

- **Feature extraction & scoring** (`flybot/evaluation/`) — a real weighted
  model with real hard-filter logic, exercised by unit tests in `tests/`
- **Decision logic** (`flybot/decision/`) — real BUY/SKIP/HOLD/SELL rules:
  take-profit, stop-loss, trailing stop, time stop, confidence decay
- **Risk management** (`flybot/risk/`) — a real state machine for position
  sizing, exposure caps, a daily circuit breaker, and loss-streak cooldowns
- **Portfolio accounting** (`flybot/execution/portfolio.py`) — real cash/
  holdings/PnL bookkeeping
- **The trading loop** (`flybot/execution/trader.py`) — the real
  orchestration order: scan → evaluate → decide → risk-check → execute →
  monitor → exit

If you swapped `SimulatedAdapter` for a real, read-only market-data adapter
tomorrow, none of the code in the bullet list above would need to change.
That's the point of the `MarketAdapter` interface in
`flybot/adapters/base.py`.

## What plugging in a real adapter would actually require

This repository does not include one, and building one is a meaningfully
larger undertaking than it might look from the interface. At minimum, a
real adapter would need to:

1. Subscribe to or poll a real new-pair feed (a DEX aggregator API, or
   direct RPC log subscriptions) for `poll_new_pairs()`.
2. Query real on-chain state for `get_snapshot()` — liquidity, holder
   distribution, mint/freeze authority, LP lock status — from a trusted
   indexer or by decoding on-chain accounts directly. Note: unlike the
   simulator, real safety flags need independent verification; various
   third-party "safety score" APIs can themselves be gamed.
3. Read prices from a real price feed or pool state for `get_price()`.
4. For `execute_buy()`/`execute_sell()`: construct, sign (using key
   material never read into this codebase's model/decision layers), and
   submit real transactions, then handle partial fills, failed
   transactions, and slippage explicitly, none of which the simulator
   models.

None of this is provided here on purpose. See `SECURITY.md` for why, and
for what independent verification you'd want before trusting this (or
any) automated strategy with real capital.
