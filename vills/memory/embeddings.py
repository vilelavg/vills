"""Geração de embeddings. Abstrai o provedor para facilitar troca/teste."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Interface de um provedor de embeddings. Permite mock em testes."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class AnthropicEmbeddingProvider:
    """Provedor real. Recebe um client já configurado (injeção de dependência)."""

    def __init__(self, client, model: str = "voyage-3") -> None:
        # Anthropic recomenda Voyage para embeddings; client é injetado
        self._client = client
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embed(texts=texts, model=self._model)
        return resp.embeddings


class EmbeddingService:
    """Orquestra geração de embeddings com um provedor plugável."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def embed_one(self, text: str) -> list[float]:
        result = await self._provider.embed([text])
        return result[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._provider.embed(texts)
