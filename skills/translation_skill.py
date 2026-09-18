"""Translation Skill."""
from __future__ import annotations

from typing import Any

from skills.base_skill import BaseSkill, skill_registry
from tools.llm_client import GroqLLMClient


TRANSLATE_PROMPT = """Sen ceviri uzmanisin. Metni hedef dile cevir.
SADECE ceviriyi yaz.
Hedef dil: {target_lang}
"""


class TranslationSkill(BaseSkill):
    name = "translation"
    description = "Ceviri yapar"

    def __init__(self) -> None:
        super().__init__()
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def execute(self, text: str = "", target_lang: str = "en", source_lang: str = "auto", **kwargs) -> dict[str, Any]:
        if not text:
            return {"error": "Metin bos"}
        lang_names = {"tr": "Turkce", "en": "Ingilizce", "de": "Almanca",
                      "fr": "Fransizca", "es": "Ispanyolca", "ru": "Rusca"}
        target_name = lang_names.get(target_lang, target_lang)
        try:
            translation = self.llm.chat(
                prompt=f"Metin: {text}",
                system=TRANSLATE_PROMPT.format(target_lang=target_name),
            )
            return {"original": text, "translation": translation.strip(),
                    "source_lang": source_lang, "target_lang": target_lang}
        except Exception as e:
            return {"error": f"Hata: {str(e)}"}


skill_registry.register(TranslationSkill())
