def gemini_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
