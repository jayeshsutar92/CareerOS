from app.ai.models import CostBreakdown, TokenUsage
from app.core.config import get_settings


def calculate_cost(usage: TokenUsage) -> CostBreakdown:
    settings = get_settings()
    input_cost = (usage.prompt_tokens / 1_000_000) * settings.ai_input_token_cost_per_1m
    output_cost = (usage.completion_tokens / 1_000_000) * settings.ai_output_token_cost_per_1m
    total_cost = input_cost + output_cost
    return CostBreakdown(
        input_cost=round(input_cost, 8),
        output_cost=round(output_cost, 8),
        total_cost=round(total_cost, 8),
    )
