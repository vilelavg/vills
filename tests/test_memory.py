import pytest

from vills.memory.embeddings import EmbeddingService
from vills.memory.hybrid_search import HybridSearch


class _FakeProvider:
    """Provider de embedding fake: vetor determinístico, sem chamar API."""

    async def embed(self, texts):
        return [[0.1] * 1536 for _ in texts]


async def test_embedding_service_embed_one():
    svc = EmbeddingService(_FakeProvider())
    vec = await svc.embed_one("texto")
    assert len(vec) == 1536


async def test_embedding_service_empty_list():
    svc = EmbeddingService(_FakeProvider())
    assert await svc.embed_many([]) == []


def test_hybrid_search_rejects_invalid_weights():
    svc = EmbeddingService(_FakeProvider())
    with pytest.raises(ValueError):
        HybridSearch(session=None, embeddings=svc, vector_weight=1.5)


def test_hybrid_search_accepts_valid_weights():
    svc = EmbeddingService(_FakeProvider())
    hs = HybridSearch(
        session=None, embeddings=svc, vector_weight=0.7, lexical_weight=0.3
    )
    assert hs._vw == 0.7
    assert hs._lw == 0.3
