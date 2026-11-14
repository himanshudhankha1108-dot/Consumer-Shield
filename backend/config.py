"""
ConsumerShield — Backend Configuration
Grok API (xAI) client setup with OpenAI-compatible endpoint.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
import instructor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# --------------- LLM API Configuration (Groq / xAI) ---------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# Determine which API provider to use
if GROQ_API_KEY or (XAI_API_KEY and XAI_API_KEY.startswith("gsk_")):
    ACTIVE_API_KEY = GROQ_API_KEY or XAI_API_KEY
    API_BASE_URL = "https://api.groq.com/openai/v1"
    TEXT_MODEL = "openai/gpt-oss-120b"
    VISION_MODEL = "openai/gpt-oss-120b"
    INSTRUCTOR_MODE = instructor.Mode.JSON
else:
    ACTIVE_API_KEY = XAI_API_KEY
    API_BASE_URL = "https://api.x.ai/v1"
    TEXT_MODEL = "grok-3-mini"
    VISION_MODEL = "grok-2-vision-1212"
    INSTRUCTOR_MODE = instructor.Mode.TOOLS

def get_grok_client() -> OpenAI:
    """Raw OpenAI-compatible client pointing to Groq or xAI endpoint."""
    if not ACTIVE_API_KEY:
        raise ValueError(
            "API Key not set. Add GROQ_API_KEY or XAI_API_KEY to your .env file."
        )
    return OpenAI(api_key=ACTIVE_API_KEY, base_url=API_BASE_URL)


def get_instructor_client():
    """Instructor-patched client for guaranteed Pydantic output."""
    return instructor.from_openai(get_grok_client(), mode=INSTRUCTOR_MODE)

# --------------- Qdrant Configuration ---------------
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "consumer_policies"
QDRANT_STORAGE_PATH = os.path.join(PROJECT_ROOT, "data", "qdrant_db")

# --------------- Embedding Configuration ---------------
# RAG Knowledge Base Model (1024-dim dense embeddings)
RAG_EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
RAG_EMBEDDING_DIMENSION = 1024

# Alias for RAG modules
EMBEDDING_MODEL_NAME = RAG_EMBEDDING_MODEL_NAME
EMBEDDING_DIMENSION = RAG_EMBEDDING_DIMENSION

# Fact Ledger Deduplication Model (Kept separate as 384-dim for low-latency fact matching)
LEDGER_EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
LEDGER_EMBEDDING_DIMENSION = 384

# --------------- Application Paths ---------------
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "data", "knowledge_base")
TEST_CASES_DIR = os.path.join(PROJECT_ROOT, "data", "test_cases")
BM25_INDEX_PATH = os.path.join(PROJECT_ROOT, "data", "bm25_index.pkl")
