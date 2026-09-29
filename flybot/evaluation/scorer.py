"""
flybot.evaluation.scorer
===========================

Combines a FeatureVector into a single confidence score, after applying
hard disqualifying filters. Hard filters exist because some conditions
(honeypot, no LP protection, mint authority live) are not "a bit risky" --
they are reasons to refuse to evaluate further, no matter how good the
rest of the vector looks.
"""

from __future__ import annotations

from flybot.core.config import EvaluationConfig
from flybot.core.models import FeatureVector, MarketSnapshot, Score


def hard_filter(snap: MarketSnapshot, config: EvaluationConfig) -> str | None:
    """Returns a disqualification reason, or None if the pair passes."""
    if snap.honeypot_flag:
        return "honeypot flag set"
    if config.require_mint_authority_revoked and not snap.mint_authority_revoked:
        return "mint authority not revoked"
    if max(snap.lp_locked_pct, snap.lp_burned_pct) < config.require_lp_lock_or_burn_pct:
        return f"LP lock/burn below {config.require_lp_lock_or_burn_pct:.0f}%"
    if snap.top10_holder_pct > config.max_top10_holder_pct:
        return f"top10 holders own {snap.top10_holder_pct:.1f}% (max {config.max_top10_holder_pct:.0f}%)"
    if snap.dev_wallet_pct > config.max_dev_wallet_pct:
        return f"dev wallet holds {snap.dev_wallet_pct:.1f}% (max {config.max_dev_wallet_pct:.0f}%)"
    return None


def score_pair(snap: MarketSnapshot, features: FeatureVector, config: EvaluationConfig) -> Score:
    reason = hard_filter(snap, config)
    if reason:
        return Score(confidence=0.0, components={}, disqualified=True, disqualify_reason=reason)

    weights = config.weights
    components = {
        "liquidity_score": features.liquidity_score * weights.get("liquidity_score", 0),
        "momentum_score": features.momentum_score * weights.get("momentum_score", 0),
        "distribution_score": features.distribution_score * weights.get("distribution_score", 0),
        "safety_score": features.safety_score * weights.get("safety_score", 0),
        "activity_score": features.activity_score * weights.get("activity_score", 0),
    }
    confidence = sum(components.values())

    # freshness acts as a small multiplier rather than an additive weight --
    # a stale pair with a great score is still less interesting than a
    # fresh one with the same score.
    confidence *= (0.75 + 0.25 * features.freshness_score)

    return Score(confidence=max(0.0, min(1.0, confidence)), components=components)
