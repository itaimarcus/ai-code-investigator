from dataclasses import dataclass

from agents import RunResult


@dataclass(frozen=True)
class TokenPrices:
    """USD per 1M tokens."""

    input: float
    cached_input: float
    cache_write: float
    output: float


# Verify against https://developers.openai.com/api/docs/pricing
# cache_write uses the 30-minute cache retention price.
PRICES: dict[str, TokenPrices] = {
    "gpt-6-luna": TokenPrices(
        input=0.10, cached_input=0.01, cache_write=0.125, output=0.50
    ),
}


@dataclass
class RunMetrics:
    model: str
    requests: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_seconds: float
    estimated_cost_usd: float | None


def estimate_cost(
    model: str,
    input_tokens: int,
    cached_input_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
) -> float | None:
    prices = PRICES.get(model)
    if prices is None:
        return None

    # input_tokens includes cached and cache-write tokens; each is billed at its own rate.
    uncached_input_tokens = input_tokens - cached_input_tokens - cache_write_tokens
    total = (
        uncached_input_tokens * prices.input
        + cached_input_tokens * prices.cached_input
        + cache_write_tokens * prices.cache_write
        + output_tokens * prices.output
    )
    return total / 1_000_000


def collect_metrics(
    result: RunResult, model: str, latency_seconds: float
) -> RunMetrics:
    usage = result.context_wrapper.usage
    cached_input_tokens = usage.input_tokens_details.cached_tokens
    cache_write_tokens = usage.input_tokens_details.cache_write_tokens
    cost = estimate_cost(
        model,
        usage.input_tokens,
        cached_input_tokens,
        cache_write_tokens,
        usage.output_tokens,
    )

    return RunMetrics(
        model=model,
        requests=usage.requests,
        input_tokens=usage.input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        output_tokens=usage.output_tokens,
        reasoning_tokens=usage.output_tokens_details.reasoning_tokens,
        latency_seconds=latency_seconds,
        estimated_cost_usd=cost if cost is not None else None,
    )
