import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flybot.core.config import EvaluationConfig
from flybot.core.models import Chain, MarketSnapshot, Pair
from flybot.evaluation.features import extract_features
from flybot.evaluation.scorer import score_pair


def _pair(age_seconds: float = 10.0) -> Pair:
    import time
    return Pair(
        address="testaddr", base_symbol="TEST", quote_symbol="SOL",
        chain=Chain.SIMULATED, created_at=time.time() - age_seconds, dex="raydium-sim",
    )


def _snapshot(**overrides) -> MarketSnapshot:
    defaults = dict(
        pair=_pair(), price_usd=0.001, liquidity_usd=50_000, fdv_usd=500_000,
        volume_5m_usd=20_000, buys_5m=30, sells_5m=10, holder_count=200,
        top10_holder_pct=20.0, lp_locked_pct=90.0, lp_burned_pct=0.0,
        mint_authority_revoked=True, freeze_authority_revoked=True,
        honeypot_flag=False, dev_wallet_pct=2.0,
    )
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


def test_clean_pair_scores_high():
    config = EvaluationConfig()
    snap = _snapshot()
    features = extract_features(snap)
    score = score_pair(snap, features, config)
    assert not score.disqualified
    assert score.confidence > 0.6


def test_honeypot_is_disqualified():
    config = EvaluationConfig()
    snap = _snapshot(honeypot_flag=True)
    features = extract_features(snap)
    score = score_pair(snap, features, config)
    assert score.disqualified
    assert "honeypot" in score.disqualify_reason


def test_low_lp_lock_is_disqualified():
    config = EvaluationConfig()
    snap = _snapshot(lp_locked_pct=10.0, lp_burned_pct=0.0)
    features = extract_features(snap)
    score = score_pair(snap, features, config)
    assert score.disqualified


def test_thin_liquidity_scores_lower_than_deep_liquidity():
    config = EvaluationConfig()
    thin = _snapshot(liquidity_usd=1_500)
    deep = _snapshot(liquidity_usd=80_000)
    thin_score = score_pair(thin, extract_features(thin), config)
    deep_score = score_pair(deep, extract_features(deep), config)
    assert deep_score.confidence > thin_score.confidence
