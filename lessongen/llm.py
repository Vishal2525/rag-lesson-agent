"""Thin provider layer so the pipeline is model-agnostic.

Every call goes through `LLM.complete(role, system, user)`. `role` is one of
generate | judge | evolve | propose. Real providers ignore it; the offline mock uses it.
"""
import os


class LLM:
    name = "base"

    def complete(self, role: str, system: str, user: str, temperature: float | None = None) -> str:
        raise NotImplementedError


class AnthropicLLM(LLM):
    def __init__(self, model: str):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model
        self.name = f"anthropic:{model}"

    def complete(self, role, system, user, temperature=None):
        kwargs = dict(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            resp = self.client.messages.create(**kwargs)
        except self._anthropic.BadRequestError as e:
            # Some models reject a temperature setting; retry once without it.
            if temperature is not None and "temperature" in str(e).lower():
                kwargs.pop("temperature")
                resp = self.client.messages.create(**kwargs)
            else:
                raise
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class OpenAILLM(LLM):
    """Works with OpenAI or any OpenAI-compatible endpoint (set OPENAI_BASE_URL)."""

    def __init__(self, model: str):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model
        self.name = f"openai:{model}"

    def complete(self, role, system, user, temperature=None):
        kwargs = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        if temperature is not None:
            kwargs["temperature"] = temperature
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


def make_llm(provider: str, model: str | None = None) -> LLM:
    provider = (provider or os.getenv("LESSONGEN_PROVIDER", "anthropic")).lower()
    if provider == "mock":
        from .mock_llm import MockLLM

        return MockLLM()
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit(
                "ANTHROPIC_API_KEY is not set. Set it, or try the offline demo with: --provider mock"
            )
        return AnthropicLLM(model or os.getenv("LESSONGEN_MODEL", "claude-sonnet-5-5"))
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is not set.")
        return OpenAILLM(model or os.getenv("LESSONGEN_MODEL", "gpt-4o"))
    raise SystemExit(f"Unknown provider: {provider}")
