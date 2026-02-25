
# Memvid Technical Specification for Agent Zero Integration

## Executive Summary

Memvid is a **serverless, single-file AI memory system** that replaces complex RAG pipelines with a portable, infrastructure-free memory layer. This specification analyzes memvid V2 architecture, Python SDK capabilities, MCP server implementation, and provides integration recommendations for Agent Zero.

**Key Value Proposition:**
- Sub-millisecond query latency
- Single portable file (.mv2) containing data, embeddings, and indices
- Hybrid search: BM25 (Tantivy) + Vector similarity (HNSW)
- No database infrastructure required
- Offline-capable with time-travel debugging

---

## 1. Architecture Overview

### 1.1 Core Design Philosophy

Memvid draws inspiration from video encoding to organize AI memory as an **append-only sequence of Smart Frames**—immutable units that store content along with timestamps, checksums, and metadata.

### 1.2 File Format Structure (.mv2)

The `.mv2` format is a purpose-built binary format with precise layout:

| Component | Size | Purpose |
|-----------|------|--------|
| **Header** | 4KB | Magic bytes (MV2\0), version, pointers to sections |
| **WAL (Write-Ahead Log)** | 1-64MB | Crash recovery, embedded in file |
| **Data Segments** | Variable | Compressed frame payloads |
| **Lex Index** | Variable | Tantivy full-text search (BM25) |
| **Vec Index** | Variable | HNSW graph for vector similarity |
| **Time Index** | Variable | Chronological ordering |
| **TOC (Footer)** | Variable | Segment offsets, checksums |

### 1.3 Smart Frames

Frames are the core data unit in Memvid:

```python
# Frame Lifecycle
- Created: put() creates frame with monotonic ID, timestamp, content
- Active: Current frames returned by default searches
- Superseded: Replaced by newer versions (queryable for history)
- Deleted: Tombstoned but preserved (queryable for audit)
```

### 1.4 V1 vs V2 Comparison

| Aspect | V1 (Deprecated) | V2 (Current) |
|--------|-----------------|--------------|
| **File Format** | MP4 videos (QR codes) | Binary .mv2 databases |
| **Vector Search** | FAISS | HNSW + Product Quantization |
| **Full-text Search** | None | Tantivy (BM25) |
| **Crash Recovery** | None | Embedded WAL |
| **Implementation** | Python-only | Rust with multi-language bindings |
| **Language Support** | Python | Python, Node.js, CLI |

---

## 2. API Reference

### 2.1 Python SDK Installation

```bash
pip install memvid-sdk
```

**Requirements:** Python 3.8+, macOS/Linux/Windows

### 2.2 Core API Methods

| Category | Methods | Description |
|----------|---------|-------------|
| **File Operations** | `create()`, `use()`, `close()` | Create, open, close memory files |
| **Data Ingestion** | `put()`, `put_many()` | Add documents with embeddings |
| **Search** | `find()`, `ask()`, `timeline()` | Query memory |
| **Memory Cards** | `memories()`, `state()`, `enrich()` | Structured fact extraction |
| **Tables** | `put_pdf_tables()`, `list_tables()` | PDF table extraction |
| **Sessions** | `session_start()`, `session_end()` | Time-travel debugging |
| **Utilities** | `verify()`, `doctor()`, `mask_pii()` | Maintenance |

### 2.3 Quick Start Code

```python
import memvid_sdk as memvid
import os

# Create a new memory file
mem = memvid.create('knowledge.mv2')

# Add documents with metadata
mem.put(
    title='Meeting Notes',
    label='notes',
    metadata={'source': 'slack'},
    text='Alice mentioned she works at Anthropic...',
    enable_embedding=True
)

# Search with semantic similarity
results = mem.find('who works at AI companies?', k=5)
for hit in results['hits']:
    print(f"Score: {hit['score']:.3f} - {hit['preview']}")

# RAG-powered Q&A
answer = mem.ask(
    'What does Alice do?',
    model='gpt-4o-mini',
    api_key=os.environ['OPENAI_API_KEY']
)
print(answer['text'])

# Context manager for auto-cleanup
with memvid.use('basic', 'memory.mv2') as mem:
    mem.put(title='Doc', label='test', metadata={}, text='Content')
    results = mem.find('query')
```

### 2.4 Search Modes

```python
# Lexical search (BM25)
hits = mv.find("deterministic", mode="lex", k=5)

# Vector search (semantic)
hits = mv.find("AI memory systems", mode="vec", k=5)

# Hybrid search (RRF fusion - auto)
hits = mv.find("complex query", mode="auto", k=5)

# Temporal queries
timeline = mv.timeline(since=1730000000, until=1730003600, limit=10)
```

### 2.5 Permission-Aware Retrieval (ACL)

```python
hits = mv.find(
    "budget",
    mode="lex",
    k=5,
    acl_context={"tenant_id": "tenant-123", "roles": ["finance"]},
    acl_enforcement_mode="enforce",
)["hits"]
```

### 2.6 Embedding Providers

```python
from memvid_sdk.embeddings import (
    OpenAIEmbeddings,
    GeminiEmbeddings,
    MistralEmbeddings,
    CohereEmbeddings,
    VoyageEmbeddings,
    LOCAL_EMBEDDING_MODELS
)

# Cloud providers
openai = OpenAIEmbeddings(api_key=os.environ['OPENAI_API_KEY'])
gemini = GeminiEmbeddings(api_key=os.environ['GEMINI_API_KEY'])

# Local models (no API required)
mem.put(
    title='Doc',
    text='Content',
    enable_embedding=True,
    embedding_model=LOCAL_EMBEDDING_MODELS['BGE_BASE']  # 768 dims
)
```

**Local Embedding Models:**

| Model | Dimensions | Speed | Quality |
|-------|------------|-------|---------|
| `BGE_SMALL` | 384 | Fastest | Good |
| `BGE_BASE` | 768 | Fast | Better |
| `NOMIC` | 768 | Fast | Better |
| `GTE_LARGE` | 1024 | Slower | Best |

---

## 3. Hybrid Search Implementation

### 3.1 Architecture

Memvid implements hybrid search through:
1. **Lexical Index**: Tantivy-based BM25 for keyword matching
2. **Vector Index**: HNSW for semantic similarity
3. **RRF Fusion**: Reciprocal Rank Fusion to combine results

### 3.2 RRF Algorithm

```python
# RRF Score Formula
RRF_score(doc) = Σ 1/(k + rank_i)

# Where:
# - k = 60 (smoothing constant)
# - rank_i = document rank in retriever i
```

### 3.3 Cross-Encoder Reranking

Optional reranking step for maximum precision:

```python
# Reranking with ms-marco-MiniLM-L-6-v2
# Precision@5: ~92% (vs 85% for RRF alone)
# Latency: ~50ms additional
```

---

## 4. MCP Server Implementation

### 4.1 Available MCP Server

**Repository:** https://github.com/ferrants/memvid-mcp-server

```python
# server.py - MCP Implementation
import os
from mcp.server.fastmcp import FastMCP
from memvid import MemvidEncoder, MemvidChat, MemvidRetriever

PORT = os.getenv("PORT", "3000")
mcp = FastMCP("memvid", port=PORT, debug=True, log_level="DEBUG")

video = "memory.mp4"
index = "memory_index.json"

@mcp.tool()
def add_chunks(chunks: list[str]) -> str:
    encoder = MemvidEncoder(video, index)
    encoder.add_chunks(chunks)
    encoder.build_video(video, index)
    return "added chunks to memory.mp4"

@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    retriever = MemvidRetriever(video, index)
    results = retriever.search(query, top_k=top_k)
    return "\n".join(results)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 4.2 MCP Configuration

```json
{
  "mcpServers": {
    "memvid": {
      "type": "streamable-http",
      "url": "http://localhost:3000"
    }
  }
}
```

### 4.3 Running MCP Server

```bash
# Install dependencies
python3.11 -m venv my_env
. ./my_env/bin/activate
pip install -r requirements.txt

# Run server
python server.py

# Custom port
PORT=3002 python server.py
```

---

## 5. Framework Adapters

### 5.1 Available Adapters

Memvid provides pre-built adapters for major frameworks:

```python
# LangChain
mem = memvid.use('langchain', 'knowledge.mv2')
retriever = mem.as_retriever()

# LlamaIndex
mem = memvid.use('llamaindex', 'knowledge.mv2')
query_engine = mem.as_query_engine()

# CrewAI
mem = memvid.use('crewai', 'knowledge.mv2')
tools = mem.tools

# AutoGen
mem = memvid.use('autogen', 'knowledge.mv2')

# Haystack
mem = memvid.use('haystack', 'knowledge.mv2')
```

---

## 6. Performance Characteristics

### 6.1 Benchmarks

| Metric | Value |
|--------|-------|
| **P50 Latency** | 0.025ms |
| **P99 Latency** | 0.075ms |
| **Throughput** | 1,372× higher than standard systems |
| **LoCoMo Accuracy** | +35% SOTA |
| **Multi-hop Reasoning** | +76% vs industry average |
| **Temporal Reasoning** | +56% vs industry average |
| **Smart Recall** | Sub-5ms local access |

### 6.2 Scalability

- **Capacity**: Millions of text chunks in single file
- **Compression**: Efficient through video codec-inspired approach
- **Memory**: Lower RAM usage vs traditional vector databases

---

## 7. Dependencies & Installation

### 7.1 Python SDK

```bash
pip install memvid-sdk
```

### 7.2 CLI

```bash
npm install -g memvid-cli
```

### 7.3 Node.js SDK

```bash
npm install @memvid/sdk
```

### 7.4 Rust

```bash
cargo add memvid-core
```

### 7.5 Feature Flags

| Flag | Description |
|------|-------------|
| `lex` | Full-text search with BM25 (Tantivy) |
| `vec` | Vector similarity (HNSW + ONNX) |
| `clip` | CLIP visual embeddings |
| `whisper` | Audio transcription |
| `encryption` | Password-based encryption (.mv2e) |
| `pdf_extract` | PDF text extraction |
| `api_embed` | Cloud API embeddings |
| `parallel_segments` | Multi-threaded ingestion |

---

## 8. Integration Code Examples

### 8.1 Basic Agent Memory

```python
import memvid_sdk as memvid

class AgentMemory:
    def __init__(self, memory_file="agent_memory.mv2"):
        self.mem = memvid.use("basic", memory_file)

    def remember(self, text, metadata=None):
        self.mem.put(
            title=metadata.get("title", "memory"),
            label=metadata.get("label", "general"),
            metadata=metadata or {},
            text=text,
            enable_embedding=True
        )

    def recall(self, query, k=5):
        return self.mem.find(query, k=k)

    def ask(self, question, model="gpt-4o-mini"):
        return self.mem.ask(question, model=model, api_key=os.environ["OPENAI_API_KEY"])
```

### 8.2 Session Recording for Debugging

```python
# Record agent session
session_id = mem.session_start("Debug Session")

# Perform operations (all recorded)
mem.put(title="Task", label="work", metadata={}, text="Analyzed data...")
results = mem.find("roadmap", k=5)

# Add checkpoint
mem.session_checkpoint()

# End session
summary = mem.session_end()
print(f"Recorded {summary['action_count']} actions")

# Replay with different parameters
replay = mem.session_replay(session_id, adaptive=True, top_k=20)
print(f"Match rate: {replay['match_rate']:.1%}")
```

### 8.3 Entity Extraction with Memory Cards

```python
# Extract facts using rules engine
result = mem.enrich("rules")

# View extracted cards
cards = mem.memories()
print(f"Extracted {cards['count']} memory cards")

# Get entity state (O(1) lookup)
alice = mem.state("Alice")
print(alice['slots'])
# {'employer': 'Anthropic', 'role': 'Engineer'}
```

---

## 9. Recommended Integration Approach for Agent Zero

### 9.1 Architecture Recommendation

**Recommended Approach: Direct Python SDK Integration with Optional MCP Layer**

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Zero Framework                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  Memory Tools   │    │     Memvid Integration Layer    │ │
│  │  ─────────────  │    │  ─────────────────────────────  │ │
│  │  memory_save    │───▶│  MemvidMemoryManager            │ │
│  │  memory_load    │◀───│  - create_memory()              │ │
│  │  memory_forget  │    │  - put_memory()                 │ │
│  │  memory_delete  │    │  - find_memory()                │ │
│  └─────────────────┘    │  - timeline()                   │ │
│                         │  - enrich()                      │ │
│  ┌─────────────────┐    └─────────────────────────────────┘ │
│  │  MCP Server     │              │                          │
│  │  (Optional)     │              ▼                          │
│  │  ─────────────  │    ┌─────────────────────────────────┐ │
│  │  memvid://      │    │      memvid-sdk (Python)        │ │
│  └─────────────────┘    │      pip install memvid-sdk     │ │
│                         └─────────────────────────────────┘ │
│                                     │                        │
│                                     ▼                        │
│                         ┌─────────────────────────────────┐ │
│                         │      .mv2 Memory Files          │ │
│                         │  - agent_zero_memory.mv2        │ │
│                         │  - project_memories.mv2         │ │
│                         │  - knowledge_base.mv2           │ │
│                         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Implementation Plan

**Phase 1: Core Memory Tool Integration**

1. Create `MemvidMemoryManager` class in `/a0/python/helpers/memvid_memory.py`
2. Modify existing memory tools to use memvid as backend
3. Implement memory file management per user/project

**Phase 2: Enhanced Features**

1. Add entity extraction with Memory Cards
2. Implement session recording for debugging
3. Add time-travel capabilities for memory inspection

**Phase 3: MCP Server (Optional)**

1. Create memvid MCP server for external agent access
2. Implement streamable-http transport
3. Add multi-tenant support with ACL

### 9.3 Proposed Tool Modifications

```python
# /a0/python/helpers/memvid_memory.py

import memvid_sdk as memvid
from typing import Dict, Any, List, Optional
import os

class MemvidMemoryManager:
    """
    Memvid-backed memory manager for Agent Zero.
    Provides persistent, searchable memory with semantic search.
    """

    def __init__(self, memory_dir: str = "/a0/usr/memories"):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        self._active_memories: Dict[str, Any] = {}

    def get_memory_file(self, user_id: str = "default") -> str:
        return os.path.join(self.memory_dir, f"{user_id}_memory.mv2")

    def save_memory(self, text: str, metadata: Dict = None, 
                    user_id: str = "default") -> str:
        """Save memory and return memory ID."""
        mem = self._get_or_create_memory(user_id)
        result = mem.put(
            title=metadata.get("title", "memory"),
            label=metadata.get("area", "general"),
            metadata=metadata or {},
            text=text,
            enable_embedding=True
        )
        mem.close()
        return result.get("frame_id", "")

    def load_memories(self, query: str, threshold: float = 0.7,
                      limit: int = 5, user_id: str = "default",
                      filter: str = None) -> List[Dict]:
        """Load memories matching query with semantic search."""
        mem = memvid.use("basic", self.get_memory_file(user_id))
        results = mem.find(query, k=limit, mode="auto")
        mem.close()
        return results.get("hits", [])

    def delete_memories(self, query: str, threshold: float = 0.75,
                        user_id: str = "default") -> int:
        """Delete memories matching query."""
        # Memvid uses tombstone deletion
        mem = memvid.use("basic", self.get_memory_file(user_id))
        hits = mem.find(query, k=100)  # Find matching memories
        deleted = 0
        for hit in hits.get("hits", []):
            # Mark as deleted (tombstone)
            # Note: Actual API may differ
            deleted += 1
        mem.close()
        return deleted

    def get_timeline(self, user_id: str = "default", 
                     since: int = None, until: int = None) -> List[Dict]:
        """Get memory timeline for time-travel debugging."""
        mem = memvid.use("basic", self.get_memory_file(user_id))
        timeline = mem.timeline(since=since, until=until)
        mem.close()
        return timeline

    def extract_entities(self, user_id: str = "default") -> Dict:
        """Extract entities and relationships from memories."""
        mem = memvid.use("basic", self.get_memory_file(user_id))
        mem.enrich("rules")
        cards = mem.memories()
        mem.close()
        return cards

    def _get_or_create_memory(self, user_id: str):
        path = self.get_memory_file(user_id)
        if os.path.exists(path):
            return memvid.use("basic", path)
        return memvid.create(path)
```

### 9.4 Tool Integration Example

```python
# Modified memory_save tool
from python.helpers.memvid_memory import MemvidMemoryManager

def memory_save(text: str, metadata: dict = None):
    """Save memory using memvid backend."""
    manager = MemvidMemoryManager()
    memory_id = manager.save_memory(
        text=text,
        metadata=metadata or {},
        user_id=get_current_user_id()
    )
    return {"status": "saved", "id": memory_id}

def memory_load(query: str, threshold: float = 0.7, limit: int = 5):
    """Load memories with semantic search."""
    manager = MemvidMemoryManager()
    memories = manager.load_memories(
        query=query,
        threshold=threshold,
        limit=limit,
        user_id=get_current_user_id()
    )
    return {"memories": memories}
```

---

## 10. Potential Challenges & Solutions

### 10.1 Challenge: MCP Server Uses V1 API

**Issue:** Current MCP server implementation uses deprecated V1 API (MP4/QR-based)

**Solution:** Create updated MCP server using V2 Python SDK:

```python
# Updated MCP server for V2
import memvid_sdk as memvid
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("memvid-v2")

@mcp.tool()
def add_memory(text: str, title: str = "memory", label: str = "general") -> str:
    with memvid.use("basic", "memory.mv2") as mem:
        mem.put(title=title, label=label, metadata={}, text=text, enable_embedding=True)
    return f"Added memory: {title}"

@mcp.tool()
def search_memory(query: str, k: int = 5, mode: str = "auto") -> str:
    with memvid.use("basic", "memory.mv2") as mem:
        results = mem.find(query, k=k, mode=mode)
    return "\n---\n".join([h["preview"] for h in results["hits"]])

@mcp.tool()
def ask_memory(question: str, model: str = "gpt-4o-mini") -> str:
    with memvid.use("basic", "memory.mv2") as mem:
        answer = mem.ask(question, model=model, api_key=os.environ["OPENAI_API_KEY"])
    return answer["text"]

mcp.run(transport="streamable-http")
```

### 10.2 Challenge: Embedding Model Selection

**Issue:** Choosing between local and cloud embedding models

**Solution:** Configuration-based approach:

```python
# Configuration
MEMVID_CONFIG = {
    "embedding_mode": "local",  # or "cloud"
    "local_model": "BGE_BASE",  # 768 dims, good balance
    "cloud_provider": "openai",
    "offline_mode": os.environ.get("MEMVID_OFFLINE", "false").lower() == "true"
}

def get_embedding_model():
    if MEMVID_CONFIG["embedding_mode"] == "local":
        return LOCAL_EMBEDDING_MODELS[MEMVID_CONFIG["local_model"]]
    else:
        return OpenAIEmbeddings(api_key=os.environ["OPENAI_API_KEY"])
```

### 10.3 Challenge: Memory File Management

**Issue:** Managing multiple memory files per user/project

**Solution:** Hierarchical memory structure:

```
/a0/usr/memories/
├── users/
│   ├── user_001/
│   │   ├── main_memory.mv2
│   │   └── project_alpha.mv2
│   └── user_002/
│       └── main_memory.mv2
└── shared/
    ├── knowledge_base.mv2
    └── documentation.mv2
```

### 10.4 Challenge: Performance at Scale

**Issue:** Maintaining sub-millisecond latency with large memory files

**Solution:** 
1. Use product quantization for large vector indices
2. Implement memory sharding for very large datasets
3. Use local embedding models to avoid network latency

---

## 11. Final Recommendation

### Recommendation: **Hybrid Integration Approach**

Integrate memvid into Agent Zero using the following strategy:

1. **Direct Python SDK Integration** (Primary)
   - Replace current JSON-based memory with memvid backend
   - Implement `MemvidMemoryManager` as abstraction layer
   - Preserve existing memory tool API for backward compatibility

2. **Enhanced Features** (Secondary)
   - Add semantic search capabilities to memory tools
   - Implement entity extraction with Memory Cards
   - Enable time-travel debugging for agent sessions

3. **MCP Server** (Optional Extension)
   - Create V2-compatible MCP server for external access
   - Enable multi-agent memory sharing
   - Support streamable-http transport

### Key Benefits for Agent Zero

| Feature | Benefit |
|---------|--------|
| **Semantic Search** | More relevant memory recall vs keyword matching |
| **Single File Portability** | Easy backup, sync, and transfer of agent memories |
| **Time-Travel** | Debug agent behavior by replaying memory history |
| **Entity Extraction** | Automatic knowledge graph from conversations |
| **Offline Capability** | No cloud dependency for core functionality |
| **Sub-ms Latency** | No perceptible delay in memory operations |

### Implementation Priority

1. **High Priority:** Core memory backend replacement
2. **Medium Priority:** Semantic search integration
3. **Low Priority:** MCP server, advanced features

### Risk Assessment

| Risk | Mitigation |
|------|-----------|
| V1→V2 API changes | Use official V2 Python SDK with auto-updates |
| Embedding model drift | Pin specific model, implement consistency checks |
| File corruption | WAL provides crash recovery, implement backups |
| Memory file bloat | Implement pruning/archival strategies |

---

## 12. References

- **Memvid GitHub:** https://github.com/memvid/memvid
- **Python SDK Docs:** https://docs.memvid.com/sdks/python
- **V2 Blog Post:** https://memvid.com/blog/introducing-memvid-v2-portable-deterministic-memory-for-ai
- **MCP Server:** https://github.com/ferrants/memvid-mcp-server
- **PyPI Package:** https://pypi.org/project/memvid-sdk/
