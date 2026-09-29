# Contributing to FLYBOT

FLYBOT is an experiment, and the codebase is deliberately small and readable
so it can stay that way. Contributions that fit the existing shape are very
welcome.

## Ground rules

1. **No real credentials, ever.** No PRs that add wallet keys, RPC secrets,
   or API tokens -- not even as examples, not even "for testing." See
   [`docs/SIMULATION_VS_REAL.md`](docs/SIMULATION_VS_REAL.md).
2. **Every pipeline stage stays swappable.** If you're adding a new signal,
   it belongs in `flybot/evaluation/`, not hardcoded into the decision
   engine. If you're adding a new market source, implement
   `flybot.adapters.base.MarketAdapter` rather than special-casing it
   elsewhere.
3. **Tests before merge.** `flybot/evaluation` and `flybot/risk` are pure
   functions/state machines with no I/O -- there's no excuse for them not
   to be covered. Run:
   ```bash
   python -m pytest tests/ -q
   ```
4. **Explain the "why," not just the "what."** Trading logic is easy to
   write and hard to justify. PRs that change a threshold or add a filter
   should say what failure mode it's guarding against.

## Local setup

```bash
git clone https://github.com/your-org/flybot.git
cd flybot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python main.py --config config/config.example.yaml --ticks 100 --seed 1
```

## Where things live

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full pipeline
breakdown before making structural changes.

## Ideas that are especially welcome

- Additional evaluation signals (see `docs/EVALUATION.md` for the current
  feature set and how to extend it)
- A second simulated adapter archetype (e.g. one that models a specific
  historical failure mode, for backtesting the risk manager against it)
- A backtest harness that replays recorded snapshot sequences instead of
  the live random-walk simulator
- Visualization scripts that turn `logs/` output into charts

## Ideas that are not in scope for this repository

- A real execution adapter with live signing. This project is a research
  scaffold; wiring it to real funds is left as an exercise (and a
  responsibility) for anyone who forks it, not something this repo will
  ship.
