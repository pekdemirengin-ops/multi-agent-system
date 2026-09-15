"""Groq LLM istemcisi — ücretsiz tier."""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

# .env dosyasını yükle (bir kere çağrılır)
load_dotenv()

# ✅ Güncel model (llama-3.3-70b-versatile 16 Ağustos 2026'da kaldırıldı)
DEFAULT_MODEL = "openai/gpt-oss-120b"

AVAILABLE_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "llama-3.1-8b-instant",
]


class GroqLLMClient:
    """Groq API etrafında basit bir sarmalayıcı."""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY ortam değişkeni ayarlanmamış (.env dosyasını kontrol et)")
        self.client = Groq(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    def chat(self, prompt: str, system: str | None = None) -> str:
        """Tek seferlik sohbet."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
    ) -> Any:
        """Araç çağrısını destekleyen sohbet."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=0.3,
        )

    def __repr__(self) -> str:
        return f"<GroqLLMClient model={self.model}>"