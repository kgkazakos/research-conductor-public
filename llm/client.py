"""
llm/client.py

LLM provider adapter for ResearchConductor.
Switch providers via LLM_PROVIDER env var (gemini | openai | anthropic).
Gemini 3.1 Pro is the default.

The gate evaluator never imports this module — gates are pure Python.
Only the four agent nodes (study_designer, session_conductor,
response_analyzer, report_generator) use LLMClient.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional

import certifi
from dotenv import load_dotenv

load_dotenv()

# SSL fix for Python 3.14 on macOS — env vars are read by google.genai directly
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.GEMINI: "gemini-3.1-pro",      # verify model string in AI Studio
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-6",
}


class LLMClient:
    """
    Single interface for all LLM calls in ResearchConductor.
    Provider and model resolved from environment at init time.
    """

    def __init__(self) -> None:
        provider_str = os.environ.get("LLM_PROVIDER", "gemini").lower().strip()
        try:
            self.provider = LLMProvider(provider_str)
        except ValueError:
            raise ValueError(
                f"Unknown LLM_PROVIDER='{provider_str}'. "
                f"Valid: {[p.value for p in LLMProvider]}"
            )

        env_model_key = f"{provider_str.upper()}_MODEL"
        self.model = os.environ.get(env_model_key, DEFAULT_MODELS[self.provider])
        self._client = self._init_client()

    def _init_client(self):
        if self.provider == LLMProvider.GEMINI:
            import google.genai as genai
            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                raise EnvironmentError("GEMINI_API_KEY not set")
            return genai.Client(api_key=key)

        if self.provider == LLMProvider.OPENAI:
            from openai import OpenAI
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise EnvironmentError("OPENAI_API_KEY not set")
            return OpenAI(api_key=key)

        if self.provider == LLMProvider.ANTHROPIC:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise EnvironmentError("ANTHROPIC_API_KEY not set")
            return anthropic.Anthropic(api_key=key)

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate a text response from the configured provider.

        Args:
            prompt:  User-facing content.
            system:  Optional system instruction / persona.

        Returns:
            Response as a plain string.
        """
        if self.provider == LLMProvider.GEMINI:
            return self._gemini(prompt, system)
        if self.provider == LLMProvider.OPENAI:
            return self._openai(prompt, system)
        if self.provider == LLMProvider.ANTHROPIC:
            return self._anthropic(prompt, system)

    # ── Provider implementations ──────────────────────────────────────────────

    def _gemini(self, prompt: str, system: Optional[str]) -> str:
        import google.genai.types as t
        cfg = t.GenerateContentConfig(temperature=0.7)
        if system:
            cfg.system_instruction = system
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        return response.text

    def _openai(self, prompt: str, system: Optional[str]) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _anthropic(self, prompt: str, system: Optional[str]) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text