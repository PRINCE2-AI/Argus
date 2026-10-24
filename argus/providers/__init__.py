"""Provider registry and automatic provider selection."""

from .. import config
from .anthropic import AnthropicProvider
from .base import Provider, ProviderError, ensure_call_ids, usage_dict
from .gemini import GeminiProvider
from .openai import (
    GroqProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)

_REGISTRY = {
    "gemini": GeminiProvider,
    "openai": OpenAICompatibleProvider,
    "openrouter": OpenRouterProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
}

_ALIASES = {
    "google": "gemini",
    "openai-compatible": "openai",
    "oai": "openai",
}


def infer_provider(model=None, base_url=None):
    """Infer a provider from an explicit environment setting or model name."""
    configured = config.env("ARGUS_PROVIDER")
    if configured:
        return _ALIASES.get(configured.lower(), configured.lower())
    if base_url or config.env("ARGUS_BASE_URL"):
        return "openai"
    if not model:
        return "gemini"
    name = model.lower()
    if name.startswith("claude"):
        return "anthropic"
    if name.startswith(("gpt", "o1", "o3", "o4", "o5", "chatgpt")):
        return "openai"
    if "/" in name:
        return "openrouter"
    return "gemini"


def get_provider(name=None, model=None, api_key=None, base_url=None, **kwargs):
    """Create a provider by name, inferring one when no name is given."""
    chosen = name or infer_provider(model=model, base_url=base_url)
    chosen = _ALIASES.get(str(chosen).lower(), str(chosen).lower())
    provider_class = _REGISTRY.get(chosen)
    if provider_class is None:
        choices = ", ".join(sorted(_REGISTRY))
        raise ProviderError(
            f"Unknown provider {chosen!r}; choose one of: {choices}"
        )
    return provider_class(
        model=model, api_key=api_key, base_url=base_url, **kwargs
    )


def available_providers():
    """Return the names accepted by :func:`get_provider`."""
    return sorted(_REGISTRY)


__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "GroqProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "Provider",
    "ProviderError",
    "available_providers",
    "ensure_call_ids",
    "get_provider",
    "infer_provider",
    "usage_dict",
]
