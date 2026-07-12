from enum import Enum
import anthropic
from .config import config


class ModelChoice(Enum):
    HAIKU = "claude-haiku-4-5-20251001"   # Klassifikation, Mini-Tasks
    SONNET = "claude-sonnet-4-6"          # Analyse, Erklärungen


class LLMClient:
    """Claude API Wrapper mit Consent-Gate. Kein direkter Anthropic-SDK-Aufruf außerhalb."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def analyze(
        self,
        prompt: str,
        model: ModelChoice = ModelChoice.SONNET,
        context: str = "",
        show_preview: bool = True,
    ) -> str:
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        if show_preview:
            preview = full_prompt[:300] + "…" if len(full_prompt) > 300 else full_prompt
            print(f"\n[LLM] Modell : {model.value}")
            print(f"[LLM] Größe  : ~{len(full_prompt)} Zeichen")
            print(f"[LLM] Inhalt : {preview}")
            answer = input("[LLM] Senden? (j/n): ").strip().lower()
            if answer != "j":
                raise RuntimeError("LLM-Aufruf vom Nutzer abgebrochen.")

        response = self._client.messages.create(
            model=model.value,
            max_tokens=4096,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.content[0].text

    def classify(self, text: str, categories: list[str]) -> str:
        """Schnelle Klassifikation mit Haiku, kein Consent-Gate."""
        prompt = (
            f"Kategorisiere diesen Text in genau eine der Kategorien: {', '.join(categories)}\n"
            f"Text: {text}\n"
            f"Antworte nur mit dem Kategorienamen."
        )
        return self.analyze(prompt, model=ModelChoice.HAIKU, show_preview=False).strip()
