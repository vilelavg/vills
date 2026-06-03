"""RAG híbrido: busca vetorial (pgvector) + lexical (BM25 via pg_trgm).

Combina os dois scores com peso configurável. Sempre filtra por tenant
para garantir isolamento de conhecimento entre agências e clientes.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vills.memory.embeddings import EmbeddingService


@dataclass
class SearchResult:
    chunk_id: uuid.UUID
    content: str
    source: str
    score: float


class HybridSearch:
    def __init__(
        self,
        session: AsyncSession,
        embeddings: EmbeddingService,
        vector_weight: float = 0.6,
        lexical_weight: float = 0.4,
    ) -> None:
        if not 0 <= vector_weight <= 1 or not 0 <= lexical_weight <= 1:
            raise ValueError("pesos devem estar entre 0 e 1")
        self._session = session
        self._embeddings = embeddings
        self._vw = vector_weight
        self._lw = lexical_weight

    async def search(
        self,
        query: str,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID | None = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Busca híbrida isolada por tenant. client_id None = escopo agência."""
        query_vec = await self._embeddings.embed_one(query)

        # Combina similaridade vetorial (1 - distância cosseno) e similaridade
        # lexical (pg_trgm). Filtro de tenant é obrigatório e vem primeiro.
        sql = text(
            """
            SELECT id, content, source,
                   (:vw * (1 - (embedding <=> :qvec)))
                 + (:lw * similarity(content, :query)) AS score
            FROM memory_chunks
            WHERE tenant_id = :tenant_id
              AND (:client_id IS NULL OR client_id = :client_id)
            ORDER BY score DESC
            LIMIT :top_k
            """
        )
        rows = await self._session.execute(
            sql,
            {
                "vw": self._vw,
                "lw": self._lw,
                "qvec": str(query_vec),
                "query": query,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "top_k": top_k,
            },
        )
        return [
            SearchResult(chunk_id=r[0], content=r[1], source=r[2], score=float(r[3]))
            for r in rows
        ]
