"""Spend tracker with a hard cap. Prices are USD per million tokens
(Claude Haiku 4.5, checked Sep 2026: $1 input, $5 output, $0.10 cache read,
$1.25 5-minute cache write). Re-check the pricing page before a big run.
"""

from act.config import MAX_USD

PRICES = {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25}


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, max_usd: float = MAX_USD):
        self.max_usd = max_usd
        self.tokens = {k: 0 for k in PRICES}

    def add(self, usage) -> None:
        self.tokens["input"] += usage.input_tokens
        self.tokens["output"] += usage.output_tokens
        self.tokens["cache_read"] += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.tokens["cache_write"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
        if self.usd > self.max_usd:
            raise BudgetExceeded(f"Spent ${self.usd:.2f} > cap ${self.max_usd:.2f}")

    @property
    def usd(self) -> float:
        return sum(self.tokens[k] * PRICES[k] / 1e6 for k in PRICES)

    def summary(self) -> str:
        t = self.tokens
        return (f"in={t['input']:,} out={t['output']:,} cache_read={t['cache_read']:,} "
                f"cache_write={t['cache_write']:,}  cost=${self.usd:.3f}")
