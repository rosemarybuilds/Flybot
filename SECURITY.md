# Security Policy

## What this project is

FLYBOT, as shipped in this repository, is a **simulation**. It trades
against a synthetic in-memory market (`flybot/adapters/simulated.py`) with
fabricated pairs and fabricated prices. It does not:

- connect to any wallet
- hold, request, or transmit a private key or seed phrase
- make any network call to a real exchange, DEX, or RPC endpoint
- move real funds under any configuration in this repository

## If you fork this to trade for real

That's outside what this repository provides or endorses, but if you do:

- Implement your own `MarketAdapter` (see `flybot/adapters/base.py`) --
  never bolt signing logic onto the scanner, evaluator, or decision engine.
- Keep key material out of source control entirely. `.env.example` shows
  the *shape* real config might take; it is not a place to put real values.
- Assume anything you read from an on-chain indexer is adversarial input.
  The scoring model in `flybot/evaluation/` treats the flags it reads
  (mint authority, LP lock, honeypot, etc.) as advisory, and you should
  independently verify any signal a third-party API gives you before
  trusting it with capital.
- Memecoin markets are adversarial by design. A well-tuned scoring model
  reduces exposure to obvious bad actors; it does not eliminate risk.

## Reporting a vulnerability

If you find a security issue in this codebase (e.g. a way the simulated
adapter could be tricked into misreporting state, or a logic bug in the
risk manager that could allow it to exceed its own limits), please open an
issue describing the flaw and a minimal reproduction. Since this project
handles no real funds or secrets, there is no private disclosure channel --
public issues are fine.
