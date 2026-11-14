"""
ConsumerShield — Production-Grade Hybrid Retriever
Combines BGE-M3 dense embeddings (1024-dim) via Qdrant with BM25Okapi sparse retrieval.
Merges candidate pools using Reciprocal Rank Fusion (RRF), applies metadata and
temporal filtering, and recovers complete statutory parent contexts for grounded generation.
"""
from __future__ import annotations

import logging
import os
import pickle
import re
from datetime import date
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from backend.config import (
    BM25_INDEX_PATH,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_STORAGE_PATH,
    RAG_EMBEDDING_MODEL_NAME,
)
from rag.ingest import get_qdrant_client, get_rag_encoder

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid dense (BGE-M3) + sparse (BM25) retriever with Reciprocal Rank Fusion.

    Dense leg searches normalized 1024-dimensional vectors in Qdrant.
    Sparse leg searches lexical tokens using BM25Okapi.
    Results are merged via RRF, temporally validated, and mapped back to parent sections.
    """

    def __init__(
        self,
        qdrant_host: str = QDRANT_HOST,
        qdrant_port: int = QDRANT_PORT,
        qdrant_path: str = QDRANT_STORAGE_PATH,
        collection_name: str = QDRANT_COLLECTION,
        bm25_index_path: str = BM25_INDEX_PATH,
    ) -> None:
        self.collection_name = collection_name
        self.bm25_index_path = bm25_index_path
        self.encoder = get_rag_encoder()
        self.qdrant = get_qdrant_client(host=qdrant_host, port=qdrant_port, path=qdrant_path)

        # BM25 state
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_chunks: List[Dict[str, Any]] = []

        if os.path.exists(bm25_index_path):
            self._load_bm25_index(bm25_index_path)
        else:
            logger.warning("BM25 index file not found at %s. Build it using rag/ingest.py", bm25_index_path)

    # ──────────── Health Check ────────────

    def health_check(self) -> Dict[str, Any]:
        """Verify the health and operational status of all retrieval sub-systems."""
        qdrant_ok = False
        vector_count = 0
        try:
            col_info = self.qdrant.get_collection(self.collection_name)
            qdrant_ok = True
            vector_count = getattr(col_info, "points_count", 0) or getattr(col_info, "vectors_count", 0) or 0
        except Exception as e:
            logger.warning("Qdrant health check warning: %s", e)

        return {
            "status": "healthy" if (qdrant_ok and self.bm25 is not None) else "degraded",
            "qdrant_connected": qdrant_ok,
            "qdrant_collection": self.collection_name,
            "indexed_vectors": vector_count,
            "bm25_indexed_chunks": len(self.corpus_chunks),
            "dense_model": RAG_EMBEDDING_MODEL_NAME,
            "embedding_dimension": 1024,
        }

    # ──────────── Embedding ────────────

    def embed_text(self, text: str) -> List[float]:
        """Encode query text into a normalized 1024-dimensional dense vector."""
        return self.encoder.encode(text, normalize_embeddings=True).tolist()

    # ──────────── Dense Search ────────────

    def dense_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Vector similarity search over child chunks via Qdrant."""
        query_vector = self.embed_text(query)
        qdrant_filter = self._build_qdrant_filter(filters) if filters else None

        results: List[Dict[str, Any]] = []

        try:
            # Compatible with both qdrant-client >= 1.20 (query_points) and earlier (search)
            if hasattr(self.qdrant, "query_points"):
                response = self.qdrant.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=qdrant_filter,
                )
                hits = response.points
            else:
                hits = self.qdrant.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=qdrant_filter,
                )

            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    {
                        "chunk_id": payload.get("chunk_id", str(hit.id)),
                        "parent_id": payload.get("parent_id"),
                        "text": payload.get("text", ""),
                        "parent_text": payload.get("parent_text", ""),
                        "score": float(hit.score),
                        "metadata": {
                            k: v
                            for k, v in payload.items()
                            if k not in ("text", "parent_text")
                        },
                    }
                )
        except Exception as exc:
            logger.error("Dense vector search failed: %s", exc)

        return results

    # ──────────── Sparse / BM25 Search ────────────

    def sparse_search(
        self, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Lexical keyword search over child chunks using BM25Okapi."""
        if self.bm25 is None or not self.corpus_chunks:
            logger.warning("BM25 index not initialized.")
            return []

        tokenized_query = re.findall(r"\w+", query.lower())
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results: List[Dict[str, Any]] = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            chunk = self.corpus_chunks[idx]
            results.append(
                {
                    "chunk_id": chunk.get("chunk_id", f"bm25_{idx}"),
                    "parent_id": chunk.get("parent_id"),
                    "text": chunk.get("text", ""),
                    "parent_text": chunk.get("parent_text", ""),
                    "score": float(scores[idx]),
                    "metadata": chunk.get("metadata", {}),
                }
            )
        return results

    # ──────────── Reciprocal Rank Fusion ────────────

    @staticmethod
    def reciprocal_rank_fusion(
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Merge ranked results from dense and sparse legs using RRF:

        RRF Score(d) = sum_{method} ( 1 / (k + rank_{method}(d)) )
        """
        fused: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_results, start=1):
            cid = item["chunk_id"]
            if cid not in fused:
                fused[cid] = {
                    **item,
                    "rrf_score": 0.0,
                    "dense_rank": rank,
                    "sparse_rank": None,
                }
            fused[cid]["rrf_score"] += 1.0 / (k + rank)

        for rank, item in enumerate(sparse_results, start=1):
            cid = item["chunk_id"]
            if cid not in fused:
                fused[cid] = {
                    **item,
                    "rrf_score": 0.0,
                    "dense_rank": None,
                    "sparse_rank": rank,
                }
            else:
                fused[cid]["sparse_rank"] = rank
            fused[cid]["rrf_score"] += 1.0 / (k + rank)

        # Update final score to rrf_score
        for item in fused.values():
            item["score"] = item["rrf_score"]

        merged = sorted(fused.values(), key=lambda d: d["score"], reverse=True)
        return merged

    # ──────────── Hybrid Search ────────────

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Combine dense semantic retrieval and sparse BM25 with RRF ranking."""
        dense = self.dense_search(query, top_k=top_k * 3, filters=filters)
        sparse = self.sparse_search(query, top_k=top_k * 3)
        fused = self.reciprocal_rank_fusion(dense, sparse, k=rrf_k)
        return fused[:top_k]

    # ──────────── Temporal Filtering ────────────

    @staticmethod
    def temporal_filter(
        results: List[Dict[str, Any]], reference_date: date
    ) -> List[Dict[str, Any]]:
        """Post-filter legal provisions to those strictly in effect on reference_date:

        effective_from <= reference_date <= effective_until (or null)
        """
        filtered: List[Dict[str, Any]] = []

        for item in results:
            meta = item.get("metadata", {})
            eff_from = meta.get("effective_from")
            eff_until = meta.get("effective_until")

            # Parse strings to date if needed
            if isinstance(eff_from, str):
                try:
                    eff_from = date.fromisoformat(eff_from[:10])
                except ValueError:
                    eff_from = None

            if isinstance(eff_until, str):
                try:
                    eff_until = date.fromisoformat(eff_until[:10])
                except ValueError:
                    eff_until = None

            # If no effective_from, consider generally applicable
            if eff_from is None:
                filtered.append(item)
                continue

            # Temporal rule validation
            if eff_from <= reference_date:
                if eff_until is None or eff_until >= reference_date:
                    filtered.append(item)

        return filtered

    # ──────────── Parent Context Recovery & Citations ────────────

    def retrieve_context(
        self,
        query: str,
        reference_date: Optional[date] = None,
        top_k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Retrieve deduplicated parent legal sections with clean statutory citations."""
        raw_results = self.hybrid_search(query=query, top_k=top_k * 2, filters=filters)

        if reference_date:
            raw_results = self.temporal_filter(raw_results, reference_date)

        # Deduplicate by parent_id so the LLM gets full section context
        seen_parents: set = set()
        deduped_sections: List[Dict[str, Any]] = []

        for item in raw_results:
            pid = item.get("parent_id") or item.get("chunk_id")
            if pid not in seen_parents:
                seen_parents.add(pid)
                meta = item.get("metadata", {})
                sec_num = meta.get("section_number") or meta.get("section_heading") or "General Provision"
                doc_title = meta.get("document_title") or meta.get("source_name") or "Legal Authority"

                deduped_sections.append(
                    {
                        "parent_id": pid,
                        "source_name": doc_title,
                        "section": sec_num,
                        "excerpt": item.get("parent_text") or item.get("text"),
                        "relevance_score": round(item.get("score", 0.0), 4),
                        "jurisdiction": meta.get("jurisdiction", "India"),
                        "effective_from": str(meta.get("effective_from")),
                        "citation": f"{doc_title}, {sec_num}",
                    }
                )

            if len(deduped_sections) >= top_k:
                break

        return {
            "query": query,
            "sections_count": len(deduped_sections),
            "sections": deduped_sections,
            "raw_hits_count": len(raw_results),
        }

    # ──────────── Helpers ────────────

    @staticmethod
    def _build_qdrant_filter(filters: Dict[str, Any]) -> Filter:
        """Translate filter dict into Qdrant Filter object."""
        must: list = []
        if "jurisdiction" in filters:
            must.append(
                FieldCondition(
                    key="jurisdiction",
                    match=MatchValue(value=filters["jurisdiction"]),
                )
            )
        if "document_type" in filters:
            must.append(
                FieldCondition(
                    key="document_type",
                    match=MatchValue(value=filters["document_type"]),
                )
            )
        return Filter(must=must)

    def _load_bm25_index(self, path: str) -> None:
        """Deserialize pickled BM25Okapi instance and corpus."""
        try:
            with open(path, "rb") as fh:
                data = pickle.load(fh)
            self.bm25 = data["bm25"]
            self.corpus_chunks = data["corpus_chunks"]
            logger.info("Loaded BM25 index with %d chunks from %s", len(self.corpus_chunks), path)
        except Exception:
            logger.exception("Failed to load BM25 index from %s", path)
