"""
flybot.evaluation.features
=============================

Turns a raw MarketSnapshot into a FeatureVector: a handful of roughly-0..1
signals that the scorer can combine. Splitting "feature extraction" from
"scoring" (see scorer.py) means you can change the weighting model without
touching how signals are computed, and vice versa.
"""

from __future__ import annotations

from flybot.core.models import FeatureVector, MarketSnapshot


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _log_scale(value: float, floor: float, ceiling: float) -> float:
    import math
    if value <= floor:
        return 0.0
    if value >= ceiling:
        return 1.0
    lo, hi, v = math.log(floor + 1), math.log(ceiling + 1), math.log(value + 1)
    return _clamp01((v - lo) / (hi - lo))


def extract_features(snap: MarketSnapshot) -> FeatureVector:
    liquidity_score = _log_scale(snap.liquidity_usd, 1_000, 100_000)

    buy_sell_total = snap.buys_5m + snap.sells_5m
    buy_pressure = (snap.buys_5m / buy_sell_total) if buy_sell_total else 0.5
    vol_to_liq = (snap.volume_5m_usd / snap.liquidity_usd) if snap.liquidity_usd else 0.0
    momentum_score = _clamp01(0.55 * buy_pressure + 0.45 * _clamp01(vol_to_liq / 1.2))

    concentration_penalty = _clamp01(snap.top10_holder_pct / 100.0)
    dev_penalty = _clamp01(snap.dev_wallet_pct / 30.0)
    holder_bonus = _log_scale(snap.holder_count, 5, 500)
    distribution_score = _clamp01(
        0.5 * (1 - concentration_penalty) + 0.3 * (1 - dev_penalty) + 0.2 * holder_bonus
    )

    lp_security = _clamp01(max(snap.lp_locked_pct, snap.lp_burned_pct) / 100.0)
    authority_security = (
        (1.0 if snap.mint_authority_revoked else 0.0)
        + (1.0 if snap.freeze_authority_revoked else 0.0)
    ) / 2.0
    honeypot_penalty = 0.0 if not snap.honeypot_flag else 1.0
    safety_score = _clamp01(
        0.45 * lp_security + 0.35 * authority_security + 0.20 * (1 - honeypot_penalty)
    )

    activity_score = _log_scale(buy_sell_total, 2, 80)

    age = snap.pair.age_seconds
    # freshness peaks shortly after listing and decays -- FLYBOT prefers
    # pairs it can still get an edge on, not ones the crowd already found.
    freshness_score = _clamp01(1.0 - (age / 600.0))

    return FeatureVector(
        liquidity_score=liquidity_score,
        momentum_score=momentum_score,
        distribution_score=distribution_score,
        safety_score=safety_score,
        activity_score=activity_score,
        freshness_score=freshness_score,
        raw={
            "buy_pressure": buy_pressure,
            "vol_to_liq": vol_to_liq,
            "age_seconds": age,
        },
    )
