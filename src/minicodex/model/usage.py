"""Token → cost helpers shared by model adapters.

Prices are illustrative defaults (USD per million tokens), keyed by model id.
Adapters may supply their own pricing table later; these defaults keep cost
accounting deterministic in the absence of a live pricing source.
"""

PRICING_USD_PER_1M: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    # DeepSeek list prices (USD per 1M tokens) as (input, output).
    "deepseek-chat": (0.28, 0.42),
    "deepseek-reasoner": (0.55, 2.19),
    "deepseek-v4-flash": (0.28, 0.42),
    "deepseek-v4-pro": (1.10, 1.68),
}

DEFAULT_PRICING: tuple[float, float] = (3.0, 15.0)


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return USD cost for a model given token counts."""
    input_price, output_price = PRICING_USD_PER_1M.get(model, DEFAULT_PRICING)
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000.0
