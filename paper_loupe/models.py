"""Supported models for Paper Loupe LLM-based ranking."""

from typing import Dict, Literal, TypedDict


class PricingInfo(TypedDict):
    input: float
    output: float
    currency: str


class ModelInfo(TypedDict):
    name: str
    provider: Literal["openai", "anthropic"]
    api_model_id: str
    description: str
    context_window: int
    pricing: PricingInfo
    max_tokens_default: int


# Dictionary of supported models with their details
SUPPORTED_MODELS: Dict[str, ModelInfo] = {
    "gpt-4o": {
        "name": "GPT-4o",
        "provider": "openai",
        "api_model_id": "gpt-4o",
        "description": "OpenAI's most capable model, optimized for chat",
        "context_window": 128000,
        "pricing": {
            "input": 2.50,  # Cost per 1M input tokens in USD
            "output": 10.00,  # Cost per 1M output tokens in USD
            "currency": "USD",
        },
        "max_tokens_default": 1024,
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "openai",
        "api_model_id": "gpt-4o-mini",
        "description": "Smaller, faster, and more affordable version of GPT-4o",
        "context_window": 128000,
        "pricing": {
            "input": 0.15,  # Cost per 1M input tokens in USD
            "output": 0.60,  # Cost per 1M output tokens in USD
            "currency": "USD",
        },
        "max_tokens_default": 1024,
    },
    "claude-3-7-sonnet": {
        "name": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "api_model_id": "claude-3-7-sonnet-20240229",
        "description": "Anthropic's advanced model with strong reasoning capabilities",
        "context_window": 200000,
        "pricing": {
            "input": 3.00,  # Cost per 1M input tokens in USD
            "output": 15.00,  # Cost per 1M output tokens in USD
            "currency": "USD",
        },
        "max_tokens_default": 4096,
    },
    "claude-3-5-haiku": {
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "api_model_id": "claude-3-5-haiku-20240307",
        "description": "Anthropic's smaller, faster model with excellent capabilities",
        "context_window": 200000,
        "pricing": {
            "input": 0.80,  # Cost per 1M input tokens in USD
            "output": 4.00,  # Cost per 1M output tokens in USD
            "currency": "USD",
        },
        "max_tokens_default": 4096,
    },
}
