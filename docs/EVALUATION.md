# Evaluation: Features and Scoring

`flybot/evaluation/features.py` + `flybot/evaluation/scorer.py`

This is where FLYBOT decides whether a pair is *interesting*, as distinct
from whether FLYBOT can *afford* to trade it (that's risk management) or
whether it's currently *worth entering* (that's the decision engine).
Evaluation happens in two steps for the same reason a lens has separate
elements: each does one job well, and you can swap one without redesigning
the whole thing.

## Step 1 — Feature extraction

`extract_features(snapshot) -> FeatureVector`

Raw on-chain/market numbers are transformed into six roughly-`0..1`
signals:

| Feature | Derived from | Intuition |
|---|---|---|
| `liquidity_score` | `liquidity_usd`, log-scaled between $1k and $100k | More liquidity = more room to actually get filled and exit |
| `momentum_score` | buy/sell ratio (5m) + volume-to-liquidity ratio | Are more people buying than selling, and is trading active relative to pool size |
| `distribution_score` | top-10 holder %, dev wallet %, holder count | Is ownership spread out, or concentrated in wallets that can dump on everyone else |
| `safety_score` | LP lock/burn %, mint/freeze authority status, honeypot flag | Structural rug indicators |
| `activity_score` | total buys+sells in the last 5 minutes, log-scaled | Is anything actually happening, or is this pair dead on arrival |
| `freshness_score` | pair age, linear decay over 10 minutes | FLYBOT is a new-pair strategy; edge decays as the crowd catches up |

Log-scaling liquidity and activity (`_log_scale` in `features.py`) matters
because these values span orders of magnitude -- the difference between
$500 and $5,000 of liquidity is a much bigger deal than the difference
between $500,000 and $505,000.

## Step 2 — Hard filters

Before anything is scored, `hard_filter()` checks a short list of
conditions that are not "slightly risky," they're **disqualifying**:

- honeypot flag set
- mint authority not revoked (if `require_mint_authority_revoked`)
- LP lock/burn below `require_lp_lock_or_burn_pct`
- top-10 holder concentration above `max_top10_holder_pct`
- dev wallet holdings above `max_dev_wallet_pct`

Any one of these returns a disqualification reason and the pair never
reaches scoring. This mirrors how a careful human trader actually works:
some checks are gates, not inputs to a weighted average. A pair with a
honeypot flag and an otherwise perfect feature vector is still a pair you
don't touch.

## Step 3 — Weighted scoring

Pairs that pass the hard filters get a `confidence` score:

```
confidence = Σ (feature_i × weight_i)   for liquidity, momentum, distribution, safety, activity
confidence *= (0.75 + 0.25 × freshness_score)
```

Weights live in `evaluation.weights` in config and default to:

```yaml
liquidity_score:     0.20
momentum_score:      0.25
distribution_score:  0.20
safety_score:        0.25
activity_score:      0.10
```

Freshness is applied as a **multiplier**, not an additive term, so it acts
as a discount on an otherwise-good score rather than something that can
inflate a mediocre one. A 9-minute-old pair with great fundamentals still
scores lower than the same pair would have at 30 seconds old, but it isn't
thrown out entirely the way a hard filter would.

`Score.components` retains the per-feature contribution so every decision
is explainable after the fact -- see the `[EVAL]` log lines and the
`reasoning` field on `Decision`.

## Extending the model

Adding a new signal is a two-line change in the common case:

1. Compute a new `0..1` feature in `extract_features()` (or add a new
   field to `FeatureVector`).
2. Add a weight for it in `EvaluationConfig.weights` and reference it in
   `score_pair()`.

Because `Score.components` is just a dict, the explainability and logging
automatically pick up new signals without further changes.
