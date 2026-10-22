"""Inference endpoints plugin: OpenAI-compatible endpoints (e.g. Ollama) as LLM providers."""

from .plugin import InferenceEndpointsPlugin
from .routes import router

__all__ = ["InferenceEndpointsPlugin", "router"]
