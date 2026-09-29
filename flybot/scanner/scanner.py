"""
flybot.scanner.scanner
=========================

The scanner is FLYBOT's compound eye. Its only job is: find new pairs,
throw away the ones too old/young or obviously too thin to matter, and
de-duplicate. It does NOT decide whether to trade -- that's the evaluator
and decision engine's job. Keeping the scanner "dumb" means it stays fast,
which matters because new-pair windows are short.
"""

from __future__ import annotations

import time
from collections import deque

from flybot.adapters.base import MarketAdapter
from flybot.core.config import ScannerConfig
from flybot.core.models import Pair


class PairScanner:
    def __init__(self, adapter: MarketAdapter, config: ScannerConfig):
        self._adapter = adapter
        self._config = config
        self._seen: dict[str, float] = {}
        self._recent: deque[str] = deque()

    def _prune_seen(self) -> None:
        cutoff = time.time() - self._config.dedupe_window_seconds
        while self._recent and self._seen.get(self._recent[0], 0) < cutoff:
            addr = self._recent.popleft()
            self._seen.pop(addr, None)

    def _passes_prefilter(self, pair: Pair) -> bool:
        age = pair.age_seconds
        if age < self._config.min_pair_age_seconds:
            return False
        if age > self._config.max_pair_age_seconds:
            return False
        if pair.chain.value not in self._config.chains:
            return False
        return True

    def scan(self) -> list[Pair]:
        """One polling cycle. Returns pairs that are new, fresh enough, and
        not already tracked."""
        self._prune_seen()
        candidates = self._adapter.poll_new_pairs()
        fresh: list[Pair] = []
        for pair in candidates:
            if pair.address in self._seen:
                continue
            if not self._passes_prefilter(pair):
                continue
            self._seen[pair.address] = time.time()
            self._recent.append(pair.address)
            fresh.append(pair)
        return fresh
