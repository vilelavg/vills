"""ContextCompressor — reduz histórico longo antes de montar o prompt.
Resolve o ponto de compressão de contexto do diagnóstico."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CompressionResult:
    messages: list[dict[str, Any]]
    original_count: int
    compressed_count: int
    was_compressed: bool


class ContextCompressor:
    def __init__(
        self,
        max_messages: int = 20,
        keep_recent: int = 8,
    ) -> None:
        if keep_recent >= max_messages:
            raise ValueError("keep_recent deve ser menor que max_messages")
        self._max_messages = max_messages
        self._keep_recent = keep_recent

    def compress(self, messages: list[dict[str, Any]]) -> CompressionResult:
        """Mantém as mensagens recentes intactas e condensa as antigas
        num único bloco de resumo. Determinístico — sem chamada de modelo."""
        original = len(messages)
        if original <= self._max_messages:
            return CompressionResult(
                messages=messages,
                original_count=original,
                compressed_count=original,
                was_compressed=False,
            )

        recent = messages[-self._keep_recent :]
        older = messages[: -self._keep_recent]

        summary_text = self._summarize_older(older)
        summary_message = {
            "role": "user",
            "content": f"[Resumo de {len(older)} mensagens anteriores]\n{summary_text}",
        }

        compressed = [summary_message, *recent]
        return CompressionResult(
            messages=compressed,
            original_count=original,
            compressed_count=len(compressed),
            was_compressed=True,
        )

    @staticmethod
    def _summarize_older(messages: list[dict[str, Any]]) -> str:
        """Resumo determinístico: junta o texto das mensagens antigas.
        Numa evolução, isto chama o Haiku para sumarizar de fato."""
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if isinstance(content, str):
                snippet = content[:200]
                parts.append(f"{role}: {snippet}")
        return "\n".join(parts)
