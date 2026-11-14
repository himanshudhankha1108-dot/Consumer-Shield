# 🛡️ ConsumerShield 2.0
### AI-Powered Consumer Evidence Intelligence & Case-Readiness System

> **Core Engineering Philosophy:**  
> *LLMs understand and extract unstructured information. Deterministic Python calculates dates and verifies rules. Hybrid RAG provides authoritative statutory and platform context. Every conclusion must have traceable evidence.*

---

## 📌 Problem Statement

Consumers facing defective products, denied refunds, warranty rejections, or unresolved e-commerce complaints often struggle to organise the evidence needed to pursue a resolution. Relevant information is scattered across purchase invoices, warranty cards, return policies, product photographs, emails, and WhatsApp customer-support conversations.

Existing legal chatbots offer generic legal text or write template complaints, but fail to:
1. Reconstruct chronological timelines with mathematical certainty.
2. Calculate return and warranty windows deterministically (LLMs hallucinate calendar arithmetic).
3. Identify missing evidence and evidentiary contradictions across documents.
4. Filter governing laws by temporal validity (e.g. 2020 E-Commerce rules vs. future amendments).

**ConsumerShield 2.0** bridges this preparation gap by compiling scattered artifacts into an **auditable, source-attributed Case-Readiness Dossier**.

---

## 🚀 Key Technical Differentiators

| Feature | Conventional Legal AI / Chatbot | ConsumerShield 2.0 Platform |
| :--- | :--- | :--- |
| **Evidence Intake** | Plain text or single PDF dump | Multi-source multimodal intake (Invoices, Warranty cards, WhatsApp, Photos) |
| **Fact Management** | Unstructured text summary | Canonical Fact Ledger with source provenance & conflict detection |
| **Date Arithmetic** | LLM probabilistic calculation | Pure Python deterministic rules engine (`dateutil`) |
| **Statutory RAG** | Naive similarity search | Hybrid Dense + BM25 with Reciprocal Rank Fusion & Temporal Filters |
| **Readiness Scoring** | Fake "win probability %" | Explainable 100-point Evidence Completeness Index with dimension weights |
| **Gap Analysis** | Assumes context is complete | Explicit Pre-Flight Checklist flagging missing photos, job-sheets, etc. |

---

## 🏛️ System Architecture

```
                                [Consumer Evidence Artifacts]
                     (Invoices, Warranty Cards, Defect Photos, WhatsApp, Emails)
                                                │
                                                ▼
                               ┌───────────────────────────────────┐
                               │ 1. Multimodal Ingestion Layer    │
                               │ - Docling / PyMuPDF Layout Parser │
                               │ - Grok-2-Vision Photo Assessment  │
                               │ - Presidio PII Redaction          │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │ 2. Structured Extraction (Pydantic│
                               │ - Strict Schema Enforcement       │
                               │ - Source Provenance & Confidence  │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │ 3. Canonical Fact Ledger          │
                               │ - Cross-document conflict detector│
                               │ - Human-in-the-loop confirmation  │
                               └─────────┬─────────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│ 4A. Deterministic Python Rules       │     │ 4B. Hybrid Statutory & Policy RAG    │
│ - Warranty expiration math           │     │ - Parent-Child Clause Chunking       │
│ - 7/10-day platform return windows   │     │ - BGE-M3 Dense + BM25 Sparse Search  │
│ - 2-year statutory limitation checks │     │ - Reciprocal Rank Fusion (RRF)       │
│ - Date contradiction verification    │     │ - Temporal metadata date filtering   │
└──────────────────┬───────────────────┘     └──────────────────┬───────────────────┘
                   │                                            │
                   └─────────────────────┬──────────────────────┘
                                         ▼
                               ┌───────────────────────────────────┐
                               │ 5. Evidence Gap & Timeline Engine │
                               │ - Chronological directed graph    │
                               │ - Required evidence presence check│
                               │ - 100-Point Completeness Scorecard│
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │ 6. Case-Readiness Dossier Export  │
                               │ - Explainable Score Breakdown     │
                               │ - Actionable Missing Proof Steps  │
                               │ - Formal Consumer Grievance Draft │
                               └───────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Engineering Justification |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Rapid interactive prototyping & demonstration dashboard |
| **API Backend** | FastAPI + Uvicorn | High-performance asynchronous REST API |
| **Extraction** | Grok API (`grok-2-latest`) + Instructor | Guaranteed Pydantic schema validation & zero hallucination extraction |
| **Vision AI** | Grok Vision (`grok-2-vision-1212`) | Visual defect observation without speculative inference |
| **Document Parsing** | Docling + PyMuPDF | Layout-aware table extraction with fallback support |
| **Vector Database** | Qdrant | Dense/sparse hybrid indexing with temporal payload filters |
| **Retrieval Fusion** | Reciprocal Rank Fusion (RRF) | Balances keyword specificity (BM25) with semantic meaning |
| **Rules Engine** | Pure Python (`dateutil.relativedelta`) | Guaranteed arithmetic correctness for legal/warranty dates |
| **Testing** | Pytest | Comprehensive unit, conflict, rules, and integration test suite |

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- (Optional) Docker for local Qdrant container

### 2. Setup Virtual Environment & Install Dependencies
```bash
cd /Users/himanshudhankhar/Documents/ConsumerShield

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and insert your credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
XAI_API_KEY=xai-your-free-grok-api-key-here
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 4. Run the Streamlit Dashboard
```bash
streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`.

### 5. Run the FastAPI Service (Optional)
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger docs available at `http://localhost:8000/docs`.

### 6. Run the Automated Test Suite
```bash
pytest tests/ -v
```

---

## 📁 Repository Directory Structure

```
ConsumerShield/
├── .env.example                   # Environment configuration template
├── requirements.txt               # Project dependencies
├── README.md                      # Architecture documentation
├── backend/
│   ├── config.py                  # Grok, Qdrant, & system configuration
│   └── main.py                    # FastAPI REST endpoints
├── ingestion/
│   ├── parser.py                  # Docling & PyMuPDF layout extraction
│   ├── vision_parser.py           # Vision LLM image damage assessment
│   └── extractor.py               # Structured Pydantic fact extraction
├── evidence/
│   ├── schemas.py                 # Core Pydantic data schemas
│   ├── ledger.py                  # Canonical Fact Ledger & conflict detector
│   ├── timeline.py                # Chronological event graph & contradictions
│   └── gap_analyzer.py            # Evidence Gap Analysis & 100-point scoring
├── rules/
│   └── engine.py                  # Deterministic Python date & warranty checks
├── rag/
│   ├── chunker.py                 # Hierarchical Parent-Child legal chunker
│   ├── retriever.py               # Hybrid Dense + BM25 + RRF + Temporal filter
│   └── ingest.py                  # Knowledge base indexer into Qdrant
├── reports/
│   └── generator.py               # Case-Readiness Dossier & complaint compiler
├── data/
│   ├── knowledge_base/            # Consumer Protection Act, E-Com Rules, Warranty guidelines
│   └── test_cases/                # 10 realistic benchmark test scenarios (JSON)
├── frontend/
│   └── app.py                     # Streamlit Interactive Dashboard
└── tests/
    ├── test_ledger.py             # Ledger & conflict detection tests
    ├── test_rules_engine.py       # Deterministic math tests
    ├── test_timeline.py           # Chronology & violation tests
    ├── test_gap_analyzer.py       # Evidence gap scorecard tests
    └── test_integration.py        # Complete end-to-end journey test
```

---

## 🔬 Benchmark Evaluation Strategy

ConsumerShield evaluates pipeline performance against 10 multi-category synthetic test cases (`data/test_cases/synthetic_cases.json`):

1. **Extraction Accuracy:** Measured via field-level precision, recall, and Macro-F1 against ground truth invoice/warranty data.
2. **Deterministic Rules Precision:** 100% binary zero-tolerance accuracy on warranty and return calculations.
3. **Retrieval MRR:** Mean Reciprocal Rank ensuring governing statutory sections appear in Top-3 retrieved chunks.
4. **Evidence Gap Detection:** Precision/Recall on identifying missing documents (e.g. unboxing photo, service center rejection sheet).

---

## ⚖️ Disclaimer

*ConsumerShield 2.0 is an evidence compilation, chronological structuring, and analytical preparation assistant. It does not provide legal representation, legal advice, or guarantee any judicial or dispute outcome. For formal adjudication, consumers should consult legal counsel or approach designated statutory forums such as the National Consumer Helpline (NCH) or Consumer Disputes Redressal Commissions.*

---

## 📄 License

MIT License. Developed for research and educational purposes.
