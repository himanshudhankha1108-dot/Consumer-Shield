"""
ConsumerShield — Knowledge Base Ingestion Pipeline
Reads legal / policy Markdown and text files, chunks them hierarchically,
embeds child chunks using BGE-M3 (1024 dimensions), and upserts into Qdrant.
Also builds a serialised BM25 index for sparse retrieval.
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import re
import socket
import uuid
from typing import Any, Dict, List, Optional, Tuple

import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from backend.config import (
    BM25_INDEX_PATH,
    KNOWLEDGE_BASE_DIR,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_STORAGE_PATH,
    RAG_EMBEDDING_DIMENSION,
    RAG_EMBEDDING_MODEL_NAME,
)
from rag.chunker import HierarchicalChunker

logger = logging.getLogger(__name__)

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_BGE_M3_ENCODER = None
_QDRANT_CLIENT = None


def get_rag_encoder() -> SentenceTransformer:
    """Singleton loader for BAAI/bge-m3 embedding model."""
    global _BGE_M3_ENCODER
    if _BGE_M3_ENCODER is None:
        logger.info("Loading RAG dense embedding model: %s", RAG_EMBEDDING_MODEL_NAME)
        _BGE_M3_ENCODER = SentenceTransformer(RAG_EMBEDDING_MODEL_NAME)
    return _BGE_M3_ENCODER


def get_qdrant_client(
    host: str = QDRANT_HOST,
    port: int = QDRANT_PORT,
    path: str = QDRANT_STORAGE_PATH,
) -> QdrantClient:
    """Connect to remote Qdrant daemon if available; otherwise use persistent local storage.
    Caches client as a process singleton and handles multi-process concurrency gracefully.
    """
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is not None:
        return _QDRANT_CLIENT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        res = sock.connect_ex((host, port))
        sock.close()
        if res == 0:
            logger.info("Connected to remote Qdrant server at %s:%d", host, port)
            _QDRANT_CLIENT = QdrantClient(host=host, port=port)
            return _QDRANT_CLIENT
    except Exception:
        pass

    os.makedirs(path, exist_ok=True)
    try:
        logger.info("Using local persistent Qdrant storage at %s", path)
        _QDRANT_CLIENT = QdrantClient(path=path)
        return _QDRANT_CLIENT
    except Exception as exc:
        import shutil
        if "already accessed by another instance" in str(exc) or "LockException" in type(exc).__name__:
            proc_path = f"{path}_proc_{os.getpid()}"
            if os.path.exists(proc_path):
                shutil.rmtree(proc_path, ignore_errors=True)
            shutil.copytree(path, proc_path, ignore=shutil.ignore_patterns(".lock"))
            logger.info("Local storage locked by server; created process snapshot at %s", proc_path)
            _QDRANT_CLIENT = QdrantClient(path=proc_path)
            return _QDRANT_CLIENT
        raise exc


def _extract_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML front-matter metadata and body text."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = text[match.end() :]
    return meta, body


def _read_files(kb_dir: str) -> List[Dict[str, Any]]:
    """Read all markdown and text files from knowledge-base directory."""
    docs: List[Dict[str, Any]] = []
    if not os.path.isdir(kb_dir):
        logger.warning("Knowledge-base directory does not exist: %s", kb_dir)
        return docs

    for filename in sorted(os.listdir(kb_dir)):
        if not filename.endswith((".md", ".txt")):
            continue
        filepath = os.path.join(kb_dir, filename)
        with open(filepath, "r", encoding="utf-8") as fh:
            raw = fh.read()
        meta, body = _extract_front_matter(raw)
        meta.setdefault("source_name", filename)
        meta.setdefault("source_file", filename)
        docs.append({"filename": filename, "metadata": meta, "body": body})
    return docs


def _detect_doc_type(filename: str) -> str:
    """Categorize document into statutory legal or platform policy."""
    lower = filename.lower()
    legal_keywords = ["act", "rule", "regulation", "section", "article", "law", "statute"]
    if any(kw in lower for kw in legal_keywords):
        return "legal"
    return "policy"


def _deterministic_point_id(doc_id: str, chunk_id: str) -> str:
    """Generate a deterministic UUID from document and chunk identifiers to prevent duplicates."""
    seed = f"{doc_id}::{chunk_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def ingest_knowledge_base(
    kb_dir: str = KNOWLEDGE_BASE_DIR,
    collection_name: str = QDRANT_COLLECTION,
    qdrant_client: Optional[QdrantClient] = None,
) -> Dict[str, Any]:
    """Read, chunk, embed with BGE-M3, and upsert knowledge base documents into Qdrant.

    Idempotent: Re-ingesting updates existing points without creating duplicates.
    """
    logger.info("Starting knowledge-base ingestion from %s", kb_dir)
    docs = _read_files(kb_dir)
    if not docs:
        logger.warning("No documents found in %s — nothing to ingest.", kb_dir)
        return {"status": "empty", "total_upserted": 0, "total_chunks": 0}

    chunker = HierarchicalChunker(max_child_size=400, child_overlap=50)
    encoder = get_rag_encoder()
    qdrant = qdrant_client or get_qdrant_client()

    existing_collections = [c.name for c in qdrant.get_collections().collections]
    if collection_name not in existing_collections:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=RAG_EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d).", collection_name, RAG_EMBEDDING_DIMENSION)

    all_child_chunks: List[Dict[str, Any]] = []
    total_parents = 0

    for doc in docs:
        doc_type = _detect_doc_type(doc["filename"])
        metadata = doc["metadata"]

        if doc_type == "legal":
            chunks = chunker.chunk_legal_document(doc["body"], metadata)
        else:
            chunks = chunker.chunk_policy_document(doc["body"], metadata)

        parents = [c for c in chunks if c["metadata"].get("chunk_type") == "parent"]
        children = [c for c in chunks if c["metadata"].get("chunk_type") == "child"]
        total_parents += len(parents)

        if not children:
            children = chunks

        all_child_chunks.extend(children)

    if not all_child_chunks:
        return {"status": "no_chunks", "total_upserted": 0, "total_chunks": 0}

    texts_to_embed = [c["text"] for c in all_child_chunks]
    embeddings = encoder.encode(
        texts_to_embed,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=False,
    )

    points: List[PointStruct] = []
    for chunk, vector in zip(all_child_chunks, embeddings):
        doc_id = chunk["metadata"].get("document_id", "doc")
        chunk_id = chunk.get("chunk_id", str(uuid.uuid4()))
        point_id = _deterministic_point_id(doc_id, chunk_id)

        payload = {
            "chunk_id": chunk_id,
            "parent_id": chunk.get("parent_id"),
            "text": chunk["text"],
            "parent_text": chunk.get("parent_text") or chunk["text"],
            **chunk["metadata"],
        }
        points.append(
            PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload=payload,
            )
        )

    batch_size = 50
    for i in range(0, len(points), batch_size):
        qdrant.upsert(
            collection_name=collection_name,
            points=points[i : i + batch_size],
        )

    logger.info("Ingested %d child chunks across %d parent sections into '%s'.", len(points), total_parents, collection_name)

    build_bm25_index(all_child_chunks=all_child_chunks)

    return {
        "status": "success",
        "total_documents": len(docs),
        "total_parents": total_parents,
        "total_upserted": len(points),
        "collection_name": collection_name,
    }


def build_bm25_index(
    kb_dir: str = KNOWLEDGE_BASE_DIR,
    all_child_chunks: Optional[List[Dict[str, Any]]] = None,
    output_path: str = BM25_INDEX_PATH,
) -> Dict[str, Any]:
    """Build and serialize BM25Okapi index over child chunks for sparse retrieval."""
    from rank_bm25 import BM25Okapi

    if all_child_chunks is None:
        docs = _read_files(kb_dir)
        chunker = HierarchicalChunker(max_child_size=400, child_overlap=50)
        all_child_chunks = []
        for doc in docs:
            doc_type = _detect_doc_type(doc["filename"])
            if doc_type == "legal":
                chunks = chunker.chunk_legal_document(doc["body"], doc["metadata"])
            else:
                chunks = chunker.chunk_policy_document(doc["body"], doc["metadata"])
            children = [c for c in chunks if c["metadata"].get("chunk_type") == "child"]
            all_child_chunks.extend(children or chunks)

    if not all_child_chunks:
        logger.warning("No chunks available — BM25 index not built.")
        return {"status": "no_chunks", "corpus_size": 0}

    tokenized_corpus = [
        re.findall(r"\w+", c["text"].lower()) for c in all_child_chunks
    ]
    bm25 = BM25Okapi(tokenized_corpus)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as fh:
        pickle.dump({"bm25": bm25, "corpus_chunks": all_child_chunks}, fh)

    logger.info("Saved BM25 index with %d chunks to %s", len(all_child_chunks), output_path)
    return {"status": "success", "corpus_size": len(all_child_chunks), "output_path": output_path}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ingest_knowledge_base()
