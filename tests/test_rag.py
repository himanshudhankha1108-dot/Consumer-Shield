"""
ConsumerShield — Comprehensive Test Suite for Hybrid RAG Pipeline
Validates chunking, BGE-M3 embeddings, dense vector search, BM25 sparse search,
RRF ranking, temporal filtering, parent recovery, and API endpoint integration.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from backend.config import KNOWLEDGE_BASE_DIR, RAG_EMBEDDING_DIMENSION
from backend.main import CASES_STORE, app
from rag.chunker import HierarchicalChunker
from rag.conversational import ConversationalLegalRAG
from rag.evaluation import RAGEvaluator
from rag.generator import GroundedLegalGenerator
from rag.ingest import ingest_knowledge_base
from rag.retriever import HybridRetriever


@pytest.fixture(scope="module")
def retriever():
    return HybridRetriever()


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestHierarchicalChunker:
    def test_parent_child_relationship(self):
        sample_doc = (
            "# Test Consumer Act\n\n"
            "### Section 2(12) — \"Defect\"\n"
            "\"Defect\" means any fault, imperfection or shortcoming in quality or standard.\n\n"
            "(1) In goods sold through e-commerce;\n"
            "(2) In services rendered by service providers.\n"
        )
        chunker = HierarchicalChunker(max_child_size=150, child_overlap=20)
        chunks = chunker.chunk_legal_document(sample_doc, {"source_name": "Test Act", "effective_from": "2020-01-01"})

        parents = [c for c in chunks if c["metadata"].get("chunk_type") == "parent"]
        children = [c for c in chunks if c["metadata"].get("chunk_type") == "child"]

        assert len(parents) == 1
        assert len(children) >= 1

        parent = parents[0]
        assert "Defect" in parent["text"]
        assert parent["metadata"]["section_number"] == "Section 2(12)"

        for child in children:
            assert child["parent_id"] == parent["chunk_id"]
            assert child["metadata"]["parent_id"] == parent["chunk_id"]
            assert child["parent_text"] == parent["text"]
            assert child["metadata"]["jurisdiction"] == "India"
            assert child["metadata"]["effective_from"] == "2020-01-01"


class TestEmbeddingsAndVectorDB:
    def test_bge_m3_embedding_dimension(self, retriever: HybridRetriever):
        vec = retriever.embed_text("Consumer dispute regarding defective laptop motherboard")
        assert len(vec) == RAG_EMBEDDING_DIMENSION
        assert len(vec) == 1024

        norm_sq = sum(x * x for x in vec)
        assert abs(norm_sq - 1.0) < 1e-3

    def test_qdrant_health_and_persistence(self, retriever: HybridRetriever):
        health = retriever.health_check()
        assert health["status"] == "healthy"
        assert health["qdrant_connected"] is True
        assert health["indexed_vectors"] > 0
        assert health["dense_model"] == "BAAI/bge-m3"


class TestRetrievalLegsAndRRF:
    def test_dense_search(self, retriever: HybridRetriever):
        hits = retriever.dense_search("manufacturing defect express warranty liability", top_k=3)
        assert len(hits) > 0
        assert "chunk_id" in hits[0]
        assert "parent_text" in hits[0]
        assert hits[0]["score"] > 0.0

    def test_sparse_bm25_search(self, retriever: HybridRetriever):
        hits = retriever.sparse_search("Section 69 limitation period two years", top_k=3)
        assert len(hits) > 0
        assert any("69" in h["text"] or "limitation" in h["text"].lower() for h in hits)

    def test_reciprocal_rank_fusion(self):
        dense_results = [
            {"chunk_id": "docA", "text": "A", "score": 0.95},
            {"chunk_id": "docB", "text": "B", "score": 0.85},
        ]
        sparse_results = [
            {"chunk_id": "docB", "text": "B", "score": 12.5},
            {"chunk_id": "docC", "text": "C", "score": 8.0},
        ]

        fused = HybridRetriever.reciprocal_rank_fusion(dense_results, sparse_results, k=60)
        assert len(fused) == 3
        assert fused[0]["chunk_id"] == "docB"
        assert fused[0]["score"] == (1.0 / (60 + 2)) + (1.0 / (60 + 1))

    def test_temporal_filtering(self):
        test_hits = [
            {
                "chunk_id": "old_rule",
                "metadata": {"effective_from": "2018-01-01", "effective_until": "2021-12-31"},
            },
            {
                "chunk_id": "current_act",
                "metadata": {"effective_from": "2020-07-20", "effective_until": None},
            },
            {
                "chunk_id": "future_amendment",
                "metadata": {"effective_from": "2027-01-01", "effective_until": None},
            },
        ]

        ref_date = date(2026, 2, 15)
        filtered = HybridRetriever.temporal_filter(test_hits, ref_date)

        passed_ids = [h["chunk_id"] for h in filtered]
        assert "current_act" in passed_ids
        assert "old_rule" not in passed_ids
        assert "future_amendment" not in passed_ids


class TestContextRecoveryAndCitations:
    def test_retrieve_context_groups_parents(self, retriever: HybridRetriever):
        context = retriever.retrieve_context("defective screen warranty repair rejected", top_k=3)
        assert context["sections_count"] <= 3
        assert len(context["sections"]) > 0

        first_sec = context["sections"][0]
        assert "citation" in first_sec
        assert "source_name" in first_sec
        assert "section" in first_sec
        assert "relevance_score" in first_sec
        assert len(first_sec["excerpt"]) > 0


class TestAPIIntegration:
    def test_rag_health_endpoint(self, api_client: TestClient):
        resp = api_client.get("/api/rag/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["indexed_vectors"] > 0

    def test_analyze_endpoint_invokes_dynamic_rag(self, api_client: TestClient):
        create_res = api_client.post("/api/cases", json={"dispute_type": "defective_product", "title": "Test RAG"})
        case_id = create_res.json()["case_id"]

        case = CASES_STORE[case_id]
        from evidence.schemas import FactItem, DocumentType
        case["ledger"].record_fact(
            FactItem(field_name="product_name", value="Asus ROG Zephyrus G14", source_doc_type=DocumentType.INVOICE, source_filename="inv.txt")
        )
        case["ledger"].record_fact(
            FactItem(field_name="defect_description", value="Screen short circuit display failure", source_doc_type=DocumentType.JOB_SHEET, source_filename="rep.txt")
        )
        case["ledger"].record_fact(
            FactItem(field_name="seller_response", value="Free warranty repair rejected", source_doc_type=DocumentType.EMAIL, source_filename="email.txt")
        )

        an_resp = api_client.post(f"/api/cases/{case_id}/analyze")
        assert an_resp.status_code == 200
        report = an_resp.json()

        policies = report.get("relevant_policies", [])
        assert len(policies) > 0
        assert any("RRF Score" in p.get("relevance", "") for p in policies)
        assert any("Consumer Protection" in p.get("source_name", "") or "Warranty" in p.get("source_name", "") for p in policies)

    def test_conversational_chat_endpoint(self, api_client: TestClient):
        create_res = api_client.post("/api/cases", json={"dispute_type": "defective_product", "title": "Test Chat"})
        case_id = create_res.json()["case_id"]

        case = CASES_STORE[case_id]
        from evidence.schemas import FactItem, DocumentType
        case["ledger"].record_fact(
            FactItem(field_name="product_name", value="Boat Rockerz 450", source_doc_type=DocumentType.INVOICE, source_filename="inv.txt")
        )

        chat_resp = api_client.post(
            f"/api/cases/{case_id}/chat",
            json={"question": "What does Section 2(12) say about defective headphones?"}
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "answer" in data
        assert len(data["citations"]) > 0
        assert "question" in data
