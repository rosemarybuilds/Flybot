# The Scanner

`flybot/scanner/scanner.py`

The scanner is FLYBOT's compound eye: hundreds of simple facets (in this
analogy, polling cycles), none individually smart, that together catch
movement other systems miss. Its job is narrow on purpose.

## What it does

On every `scan()` call:

1. Prunes its de-dupe window (`scanner.dedupe_window_seconds`) so memory
   doesn't grow unbounded over a long run.
2. Asks the active `MarketAdapter.poll_new_pairs()` for anything new.
3. Drops anything already seen inside the de-dupe window.
4. Drops anything that fails a cheap pre-filter:
   - **too young** (`min_pair_age_seconds`) -- lets the first few seconds
     of chaos (bot wars, initial LP settling) pass before FLYBOT looks at it
   - **too old** (`max_pair_age_seconds`) -- FLYBOT is a *new-pair* strategy;
     if a pair's been live for 10 minutes, the edge this system is built
     for has already decayed
   - **wrong chain** -- only chains listed in `scanner.chains` are considered
5. Returns the surviving list as `Pair` objects for the evaluator.

## What it deliberately does not do

The scanner has no opinion about liquidity depth, holder distribution,
contract safety, or momentum. All of that lives in `flybot/evaluation/`.
This split exists because:

- The scanner needs to be **fast** -- new-pair windows are short, and
  every millisecond spent here is a millisecond not spent evaluating a
  pair that might actually be worth trading.
- Pre-filtering and scoring have different failure costs. A scanner bug
  that lets through a bad pair costs one wasted evaluation. An evaluator
  bug that scores a rug highly costs money. Keeping the scanner dumb keeps
  its surface area for bugs small.

## Extending it

To scan additional chains, plug in a `MarketAdapter` that returns pairs
tagged with the new `Chain` value (see `flybot/core/models.py`) and add
that value to `scanner.chains` in your config. No change to
`PairScanner` itself should be necessary.

To scan multiple sources concurrently in a real deployment, the intended
pattern is one `MarketAdapter` per source, each with its own `PairScanner`
instance, feeding a shared queue that the evaluator pulls from -- rather
than teaching a single scanner to know about multiple backends.
