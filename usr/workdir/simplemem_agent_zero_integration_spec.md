# SimpleMem Integration Technical Specification for Agent Zero

## Executive Summary

SimpleMem is an efficient lifelong memory framework for LLM agents that achieves **43.24% F1 score** on the LoCoMo benchmark while using **~550 tokens per query** (30× reduction vs full-context approaches). This specification details how to integrate SimpleMem's semantic compression and multi-view retrieval into Agent Zero's memory pipeline.

---

## 1. Architecture Overview

### 1.1 Three-Stage Pipeline

SimpleMem implements a three-stage memory processing pipeline:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SimpleMem Architecture                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │  Stage 1         │    │  Stage 2         │    │  Stage 3      │ │
│  │  Semantic        │───▶│  Online          │───▶│  Intent-Aware │ │
│  │  Compression     │    │  Synthesis       │    │  Retrieval    │ │
│  └──────────────────┘    └──────────────────┘    └───────────────┘ │
│         │                        │                      │         │
│         ▼                        ▼                      ▼         │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐     │
│  │ MemoryBuilder│    │ Consolidation    │    │HybridRetriever│     │
│  │              │    │ Worker           │    │               │     │
│  │ - Φ_gate     │    │ - Decay          │    │ - Planning    │     │
│  │ - Φ_extract  │    │ - Merge          │    │ - Reflection  │     │
│  │ - Φ_coref    │    │ - Prune          │    │ - Multi-view  │     │
│  │ - Φ_time     │    │                  │    │               │     │
│  └──────────────┘    └──────────────────┘    └───────────────┘     │
│         │                        │                      │         │
│         └────────────────────────┼──────────────────────┘         │
│                                  ▼                                 │
│                    ┌──────────────────────────┐                    │
│                    │     VectorStore          │                    │
│                    │     (LanceDB)            │                    │
│                    │                          │                    │
│                    │  ┌────────────────────┐  │                    │
│                    │  │ Semantic (Dense)   │  │                    │
│                    │  │ Lexical (BM25)     │  │                    │
│                    │  │ Symbolic (SQL)     │  │                    │
│                    │  └────────────────────┘  │                    │
│                    └──────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Semantic Compression Algorithm

The core innovation is **Semantic Lossless Compression** that transforms unstructured dialogues into compact, context-independent memory units:

#### Entropy-Aware Filtering (Φ_gate)
```python
# Implicit semantic density gating
# Filters low-information content using entropy threshold τ=0.35
def entropy_aware_filter(dialogue_window: List[Dialogue]) -> List[Dialogue]:
    """
    Removes:
    - Phatic chit-chat ("Okay", "Sure", "Got it")
    - Redundant confirmations
    - Low semantic density content
    """
    pass
```

#### Context Normalization
Three transformation functions applied in sequence:

```python
# Φ_extract: Extract candidate factual statements
facts = extract_facts(dialogue)

# Φ_coref: Resolve coreferences (pronouns → entities)
# "He agreed" → "Bob agreed"
resolved = resolve_coreferences(facts, dialogue_context)

# Φ_time: Convert relative timestamps → absolute ISO-8601
# "tomorrow at 2pm" → "2025-11-16T14:00:00"
normalized = normalize_timestamps(resolved, reference_time)
```

#### Lossless Restatement Example
```python
# Input Dialogue:
# "He'll meet Bob tomorrow at 2pm"

# Output Memory Entry:
MemoryEntry(
    lossless_restatement="Alice will meet Bob at Starbucks on 2025-11-16T14:00:00",
    keywords=["Alice", "Bob", "Starbucks", "meeting"],
    timestamp="2025-11-16T14:00:00",
    location="Starbucks",
    persons=["Alice", "Bob"],
    entities=[],
    topic="Meeting arrangement"
)
```

### 1.3 Multi-View Indexing (I(m_k))

Each memory unit is indexed through three complementary representations:

```python
class MemoryEntry(BaseModel):
    # Semantic Layer - Dense embeddings (1024-1536 dimensions)
    lossless_restatement: str  # → E_dense() → vector[1024]
    
    # Lexical Layer - Sparse keyword vectors
    keywords: List[str]  # → BM25 indexing
    
    # Symbolic Layer - Metadata constraints
    timestamp: Optional[str]  # ISO 8601 for time-range queries
    location: Optional[str]   # Exact location matching
    persons: List[str]        # Person entity filtering
    entities: List[str]       # Company/product filtering
    topic: Optional[str]      # Topic categorization
```

**Retrieval Formula:**
$$C_q = R_{sem} \cup R_{lex} \cup R_{sym}$$

Where:
- $R_{sem} = \text{Top-n}(\cos(E(q_{sem}), E(m_i)))$ — Semantic similarity
- $R_{lex} = \text{Top-n}(\text{BM25}(q_{lex}, m_i))$ — Keyword matching
- $R_{sym} = \text{Top-n}(\{m_i | \text{Meta}(m_i) \vDash q_{sym}\})$ — Structured filtering

---

## 2. API Reference

### 2.1 Core System API

```python
from main import SimpleMemSystem, create_system

# Initialize system
system = create_system(
    clear_db=False,
    enable_planning=True,
    enable_reflection=True,
    max_reflection_rounds=2,
    enable_parallel_processing=True,
    max_parallel_workers=4
)

# Add dialogues
system.add_dialogue(
    speaker="Alice",
    content="Bob, let's meet at Starbucks tomorrow at 2pm",
    timestamp="2025-11-15T14:30:00"
)

# Finalize input (process remaining buffer)
system.finalize()

# Query memories
answer = system.ask("When is the meeting?")
```

### 2.2 Cross-Session Orchestrator API

```python
from cross.orchestrator import create_orchestrator

async def main():
    # Create orchestrator
    orch = create_orchestrator(
        project="agent-zero",
        tenant_id="default",
        max_context_tokens=2000
    )
    
    # Start session with context injection
    result = await orch.start_session(
        content_session_id="session-001",
        user_prompt="Build a REST API for user management"
    )
    
    memory_session_id = result["memory_session_id"]
    context = result["context"]  # Pre-built context for system prompt
    
    # Record events during session
    await orch.record_message(
        memory_session_id,
        content="User requested JWT authentication",
        role="user"
    )
    
    await orch.record_tool_use(
        memory_session_id,
        tool_name="read_file",
        tool_input="auth/jwt.py",
        tool_output="class JWTHandler: ..."
    )
    
    # Finalize session (extracts observations, stores memories)
    report = await orch.stop_session(memory_session_id)
    print(f"Stored {report.entries_stored} memory entries")
    
    # End session
    await orch.end_session(memory_session_id)
    orch.close()
```

### 2.3 Direct VectorStore API

```python
from database.vector_store import VectorStore
from models.memory_entry import MemoryEntry

# Initialize
store = VectorStore(
    db_path="./lancedb_data",
    table_name="memory_entries"
)

# Add entries
entry = MemoryEntry(
    lossless_restatement="Alice discussed API design with Bob on 2025-11-15",
    keywords=["Alice", "Bob", "API", "design"],
    timestamp="2025-11-15T14:30:00",
    persons=["Alice", "Bob"],
    topic="API Design"
)
store.add_entries([entry])

# Semantic search
results = store.semantic_search(query="API discussion", top_k=5)

# Keyword search (BM25)
results = store.keyword_search(keywords=["Alice", "API"], top_k=5)

# Structured search (metadata filtering)
results = store.structured_search(
    persons=["Alice"],
    timestamp_range=("2025-11-01", "2025-11-30"),
    top_k=10
)
```

### 2.4 Consolidation Worker API

```python
from cross.consolidation import ConsolidationWorker, ConsolidationPolicy

# Configure consolidation policy
policy = ConsolidationPolicy(
    max_age_days=90,           # Age threshold for decay
    decay_factor=0.9,          # Importance multiplier
    merge_similarity_threshold=0.95,  # Cosine similarity for merging
    min_importance=0.05,       # Prune threshold
    max_entries_per_run=1000
)

# Run consolidation
worker = ConsolidationWorker(
    sqlite_storage=sqlite_storage,
    vector_store=vector_store,
    policy=policy
)

result = worker.run(tenant_id="default")
# result: ConsolidationResult(decayed_count=X, merged_count=Y, pruned_count=Z)
```

---

## 3. Integration with Agent Zero Memory System

### 3.1 Current Agent Zero Memory Architecture

Agent Zero currently provides:
- `memory_save`: Save text to long-term memory
- `memory_load`: Query memories with threshold/filter
- `memory_delete`: Delete memories by ID
- `memory_forget`: Remove memories by query

These use a simple embedding-based semantic search without:
- Structured metadata extraction
- Temporal normalization
- Multi-view indexing
- Memory consolidation

### 3.2 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│              Agent Zero + SimpleMem Integration                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User Message                                                       │
│       │                                                             │
│       ▼                                                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    Agent Zero Framework                     │    │
│  │                                                            │    │
│  │  ┌─────────────┐    ┌─────────────────────────────────┐   │    │
│  │  │ Input       │───▶│ SimpleMem Semantic Compression  │   │    │
│  │  │ Processing  │    │                                 │   │    │
│  │  └─────────────┘    │ - Extract facts                 │   │    │
│  │                     │ - Resolve coreferences          │   │    │
│  │                     │ - Normalize timestamps          │   │    │
│  │                     │ - Generate keywords             │   │    │
│  │                     └────────────┬────────────────────┘   │    │
│  │                                  │                         │    │
│  │                                  ▼                         │    │
│  │  ┌─────────────────────────────────────────────────────┐  │    │
│  │  │              Enhanced Memory Tools                   │  │    │
│  │  │                                                     │  │    │
│  │  │  memory_save_enhanced()                             │  │    │
│  │  │  - Semantic compression before storage              │  │    │
│  │  │  - Multi-view indexing                              │  │    │
│  │  │                                                     │  │    │
│  │  │  memory_load_enhanced()                             │  │    │
│  │  │  - Intent-aware retrieval planning                  │  │    │
│  │  │  - Hybrid multi-view search                         │  │    │
│  │  │  - Reflection-based refinement                      │  │    │
│  │  │                                                     │  │    │
│  │  │  memory_consolidate()                               │  │    │
│  │  │  - Decay old memories                               │  │    │
│  │  │  - Merge near-duplicates                            │  │    │
│  │  │  - Prune low-importance                             │  │    │
│  │  └─────────────────────────────────────────────────────┘  │    │
│  │                                  │                         │    │
│  │                                  ▼                         │    │
│  │  ┌─────────────────────────────────────────────────────┐  │    │
│  │  │              LanceDB + SQLite                        │  │    │
│  │  │                                                     │  │    │
│  │  │  Vector Store (Semantic)  │  SQLite (Symbolic)      │  │    │
│  │  │  Full-Text Index (Lexical)│  Session Metadata       │  │    │
│  │  └─────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Implementation: Enhanced Memory Tools

#### Tool 1: `memory_save_enhanced`

```python
# python/tools/memory_save_enhanced.py

from models.memory_entry import MemoryEntry
from core.memory_builder import MemoryBuilder
from database.vector_store import VectorStore
import config

class MemorySaveEnhanced:
    """
    Enhanced memory save with semantic compression.
    
    Replaces simple embedding storage with:
    - Fact extraction
    - Coreference resolution
    - Temporal normalization
    - Multi-view indexing
    """
    
    def __init__(self):
        self.memory_builder = MemoryBuilder(
            llm_client=get_llm_client(),
            vector_store=get_vector_store(),
            window_size=10,
            enable_parallel_processing=True
        )
    
    async def execute(self, text: str, metadata: dict = None):
        """
        Save text to memory with semantic compression.
        
        Args:
            text: Raw text to memorize
            metadata: Optional metadata (session_id, user_id, etc.)
        
        Returns:
            {
                "entry_id": "uuid",
                "lossless_restatement": "Normalized statement",
                "keywords": ["list", "of", "keywords"],
                "compression_ratio": 0.35  # Approximate
            }
        """
        # Create dialogue from text
        dialogue = Dialogue(
            dialogue_id=generate_id(),
            speaker=metadata.get("speaker", "system"),
            content=text,
            timestamp=datetime.now().isoformat()
        )
        
        # Process through semantic compression
        self.memory_builder.add_dialogue(dialogue)
        self.memory_builder.process_remaining()
        
        # Return the stored entry
        entries = self.memory_builder.vector_store.get_all_entries()
        if entries:
            latest = entries[-1]
            return {
                "entry_id": latest.entry_id,
                "lossless_restatement": latest.lossless_restatement,
                "keywords": latest.keywords,
                "timestamp": latest.timestamp,
                "persons": latest.persons,
                "entities": latest.entities,
                "topic": latest.topic
            }
```

#### Tool 2: `memory_load_enhanced`

```python
# python/tools/memory_load_enhanced.py

from core.hybrid_retriever import HybridRetriever
from typing import List, Optional

class MemoryLoadEnhanced:
    """
    Enhanced memory retrieval with intent-aware planning.
    
    Features:
    - Multi-query generation based on intent analysis
    - Hybrid retrieval (semantic + keyword + structured)
    - Reflection-based refinement
    """
    
    def __init__(self):
        self.retriever = HybridRetriever(
            llm_client=get_llm_client(),
            vector_store=get_vector_store(),
            enable_planning=True,
            enable_reflection=True,
            max_reflection_rounds=2
        )
    
    async def execute(
        self,
        query: str,
        threshold: float = 0.7,
        limit: int = 5,
        filter: str = None,
        enable_reflection: bool = True
    ) -> List[dict]:
        """
        Load memories with hybrid retrieval.
        
        Args:
            query: Search query
            threshold: Minimum similarity (not used in hybrid mode)
            limit: Maximum results
            filter: Optional Python expression filter
            enable_reflection: Enable reflection-based refinement
        
        Returns:
            [
                {
                    "entry_id": "uuid",
                    "lossless_restatement": "...",
                    "keywords": [...],
                    "timestamp": "...",
                    "persons": [...],
                    "score": 0.85
                },
                ...
            ]
        """
        # Execute hybrid retrieval
        results = self.retriever.retrieve(
            query=query,
            enable_reflection=enable_reflection
        )
        
        # Apply limit and filter
        if filter:
            results = self._apply_filter(results, filter)
        
        results = results[:limit]
        
        # Format response
        return [
            {
                "entry_id": entry.entry_id,
                "lossless_restatement": entry.lossless_restatement,
                "keywords": entry.keywords,
                "timestamp": entry.timestamp,
                "location": entry.location,
                "persons": entry.persons,
                "entities": entry.entities,
                "topic": entry.topic
            }
            for entry in results
        ]
```

#### Tool 3: `memory_consolidate`

```python
# python/tools/memory_consolidate.py

from cross.consolidation import ConsolidationWorker, ConsolidationPolicy
from datetime import datetime

class MemoryConsolidate:
    """
    Memory consolidation tool for maintenance.
    
    Implements CLS-inspired consolidation:
    - Decay: Reduce importance of old memories
    - Merge: Combine near-duplicates
    - Prune: Remove low-importance entries
    """
    
    def __init__(self):
        self.worker = ConsolidationWorker(
            sqlite_storage=get_sqlite_storage(),
            vector_store=get_vector_store(),
            policy=ConsolidationPolicy(
                max_age_days=90,
                decay_factor=0.9,
                merge_similarity_threshold=0.95,
                min_importance=0.05
            )
        )
    
    async def execute(
        self,
        max_age_days: int = 90,
        decay_factor: float = 0.9,
        merge_threshold: float = 0.95,
        min_importance: float = 0.05
    ) -> dict:
        """
        Run memory consolidation.
        
        Returns:
            {
                "decayed_count": 15,
                "merged_count": 8,
                "pruned_count": 3,
                "duration_seconds": 0.234
            }
        """
        result = self.worker.run(tenant_id="default")
        
        return {
            "decayed_count": result.decayed_count,
            "merged_count": result.merged_count,
            "pruned_count": result.pruned_count,
            "duration_seconds": result.duration_seconds
        }
```

---

## 4. Performance Characteristics

### 4.1 Token Efficiency

| Approach | Tokens/Query | Reduction vs Full Context |
|----------|-------------|---------------------------|
| Full-context (MemGPT) | ~16,900 | Baseline |
| Mem0 | ~980 | 94% |
| A-Mem | ~1,200-2,520 | 85-93% |
| **SimpleMem** | **~530-580** | **96-97% (30×)** |

### 4.2 Benchmark Performance (LoCoMo-10, GPT-4.1-mini)

| Metric | A-Mem | Mem0 | SimpleMem | Improvement |
|--------|-------|------|-----------|-------------|
| Average F1 | 32.58% | 34.20% | **43.24%** | +26.4% vs Mem0 |
| Total Time | 5937.2s | 1934.3s | **480.9s** | 4× faster than Mem0 |
| MultiHop F1 | - | 30.12% | **43.46%** | +44% improvement |
| Temporal F1 | - | 48.92% | **58.62%** | +20% improvement |

### 4.3 Overhead Analysis

```python
# Memory Processing Overhead
WINDOW_SIZE = 40 dialogues
OVERLAP_SIZE = 2 dialogues

# Per-window processing:
# - LLM call for extraction: ~0.5-2s
# - Embedding generation: ~0.1s
# - Vector storage: ~0.05s

# Retrieval overhead:
# - Intent analysis: ~0.3s (1 LLM call)
# - Multi-view search: ~0.1s (parallel)
# - Reflection (optional): ~0.5-1.5s (1-2 LLM calls)

# Consolidation overhead (periodic):
# - Decay: O(n) vector updates
# - Merge: O(n²) similarity comparisons (batch embeddings)
# - Prune: O(n) soft-deletes
```

### 4.4 Memory Requirements

```python
# Embedding model: Qwen3-Embedding-0.6B
EMBEDDING_DIMENSION = 1024
MODEL_SIZE = ~600MB (loaded once)

# LanceDB storage:
# - Per entry: ~4KB (vector + metadata)
# - 10,000 entries: ~40MB
# - Supports cloud storage (GCS, S3, Azure)

# SQLite storage:
# - Session metadata: ~1KB per session
# - Observations: ~500B per observation
```

---

## 5. Comparison with Traditional Memory Approaches

### 5.1 Feature Comparison

| Feature | Traditional RAG | Mem0 | SimpleMem |
|---------|----------------|------|-----------|
| Semantic Search | ✅ | ✅ | ✅ |
| Keyword Search | ❌ | Limited | ✅ (BM25) |
| Structured Filtering | ❌ | ❌ | ✅ (SQL) |
| Coreference Resolution | ❌ | ❌ | ✅ |
| Temporal Normalization | ❌ | ❌ | ✅ (ISO-8601) |
| Intent-Aware Retrieval | ❌ | ❌ | ✅ (Planning) |
| Reflection Refinement | ❌ | ❌ | ✅ |
| CLS-Based Consolidation | ❌ | ❌ | ✅ |
| Provenance Tracking | ❌ | ❌ | ✅ |

### 5.2 Quality vs Token Trade-off

```
Token Usage (lower is better)
     ▲
     │                                    ● Full-context (16,900)
     │
  5k ┤
     │
     │                      ● A-Mem (2,000)
  2k ┤
     │            ● Mem0 (980)
     │
   1k ┤
     │      ● SimpleMem (550) ★ Best trade-off
     │
     │
   0 ┼──────────────────────────────────────────▶
       0%      10%      20%      30%      40%      50%
                          F1 Score (higher is better)
```

### 5.3 Ablation Study Impact

| Component Removed | F1 Change | Multi-Hop Impact |
|-------------------|-----------|------------------|
| Consolidation disabled | -7.2% | -31.3% |
| Planning disabled | -5.1% | -18.5% |
| Reflection disabled | -3.8% | -12.2% |
| Multi-view indexing | -4.5% | -22.1% |

---

## 6. Implementation Recommendations

### 6.1 Phased Integration

**Phase 1: Core Infrastructure (Week 1-2)**
```python
# 1. Add dependencies
pip install lancedb sentence-transformers pydantic

# 2. Create SimpleMem instance
from main import create_system
simplemem = create_system()

# 3. Replace memory_save with memory_save_enhanced
```

**Phase 2: Hybrid Retrieval (Week 3-4)**
```python
# 1. Deploy memory_load_enhanced
# 2. Configure retrieval parameters
# 3. Enable parallel retrieval
```

**Phase 3: Cross-Session Memory (Week 5-6)**
```python
# 1. Integrate CrossMemOrchestrator
# 2. Enable session lifecycle hooks
# 3. Add context injection to system prompt
```

**Phase 4: Consolidation (Week 7-8)**
```python
# 1. Schedule periodic consolidation
# 2. Configure decay/merge/prune policies
# 3. Add memory stats dashboard
```

### 6.2 Configuration

```python
# config.py additions for Agent Zero integration

# SimpleMem Configuration
SIMPLEMEM_ENABLED = True
SIMPLEMEM_LANCEDB_PATH = "./memory/lancedb"
SIMPLEMEM_SQLITE_PATH = "./memory/simplemem.db"

# Memory Building
SIMPLEMEM_WINDOW_SIZE = 40
SIMPLEMEM_OVERLAP_SIZE = 2
SIMPLEMEM_ENABLE_PARALLEL = True
SIMPLEMEM_MAX_WORKERS = 4

# Retrieval
SIMPLEMEM_SEMANTIC_TOP_K = 25
SIMPLEMEM_KEYWORD_TOP_K = 5
SIMPLEMEM_STRUCTURED_TOP_K = 5
SIMPLEMEM_ENABLE_PLANNING = True
SIMPLEMEM_ENABLE_REFLECTION = True
SIMPLEMEM_MAX_REFLECTION_ROUNDS = 2

# Consolidation
SIMPLEMEM_MAX_AGE_DAYS = 90
SIMPLEMEM_DECAY_FACTOR = 0.9
SIMPLEMEM_MERGE_THRESHOLD = 0.95
SIMPLEMEM_MIN_IMPORTANCE = 0.05

# Context Injection
SIMPLEMEM_MAX_CONTEXT_TOKENS = 2000
```

### 6.3 System Prompt Integration

```markdown
<!-- Add to agent.system.md -->

## Memory System

You have access to an enhanced memory system with semantic compression:

1. **memory_save_enhanced**: Store information with automatic:
   - Fact extraction
   - Coreference resolution (pronouns → names)
   - Temporal normalization (relative → absolute timestamps)
   - Multi-view indexing for efficient retrieval

2. **memory_load_enhanced**: Retrieve memories with:
   - Intent-aware query planning
   - Hybrid search (semantic + keyword + structured)
   - Reflection-based result refinement

3. **memory_consolidate**: Periodic maintenance:
   - Decay old memories
   - Merge near-duplicates
   - Prune low-importance entries

Use these tools to maintain persistent, efficient memory across sessions.
```

### 6.4 Scheduled Tasks

```python
# Add consolidation as scheduled task
from scheduler import create_scheduled_task

create_scheduled_task(
    name="memory_consolidation",
    system_prompt="You are a memory maintenance agent.",
    prompt="Run memory consolidation using the memory_consolidate tool.",
    schedule={
        "minute": "0",
        "hour": "3",  # 3 AM daily
        "day": "*",
        "month": "*",
        "weekday": "*"
    },
    dedicated_context=True
)
```

---

## 7. Integration Strategy Summary

### Recommended Integration Points

1. **Replace `memory_save`** with `memory_save_enhanced`
   - Location: `python/tools/memory_save.py`
   - Benefit: 30× token reduction, structured metadata

2. **Replace `memory_load`** with `memory_load_enhanced`
   - Location: `python/tools/memory_load.py`
   - Benefit: +26% F1 score, intent-aware retrieval

3. **Add `memory_consolidate`** as new tool
   - Location: `python/tools/memory_consolidate.py`
   - Benefit: CLS-based maintenance, lifelong memory quality

4. **Add `CrossMemOrchestrator`** for session management
   - Location: `python/lib/simplemem_orchestrator.py`
   - Benefit: Cross-session context injection, provenance tracking

### Migration Path

```
Current State:
┌─────────────────────┐
│ memory_save (basic) │
│ memory_load (basic) │
│ memory_delete       │
│ memory_forget       │
└─────────────────────┘
         │
         ▼
Phase 1: Enhanced Storage
┌─────────────────────────────┐
│ memory_save_enhanced        │
│ - Semantic compression      │
│ - Multi-view indexing       │
└─────────────────────────────┘
         │
         ▼
Phase 2: Enhanced Retrieval
┌─────────────────────────────┐
│ memory_load_enhanced        │
│ - Hybrid retrieval          │
│ - Intent-aware planning     │
└─────────────────────────────┘
         │
         ▼
Phase 3: Cross-Session Memory
┌─────────────────────────────┐
│ CrossMemOrchestrator        │
│ - Session lifecycle         │
│ - Context injection         │
└─────────────────────────────┘
         │
         ▼
Phase 4: Lifelong Memory
┌─────────────────────────────┐
│ memory_consolidate          │
│ - Decay/Merge/Prune         │
│ - CLS-based maintenance     │
└─────────────────────────────┘
```

### Key Benefits for Agent Zero

1. **30× Token Efficiency**: Reduce memory-related token costs by 96-97%
2. **+26% Retrieval Quality**: Improve F1 score from 34% to 43%
3. **Structured Memory**: Enable time-based, person-based, entity-based queries
4. **Lifelong Memory**: CLS-inspired consolidation maintains quality over time
5. **Provenance Tracking**: Every memory traceable to source evidence
6. **Cross-Session Context**: Automatic injection of relevant past experiences

---

## Appendix A: Installation

```bash
# Clone SimpleMem
git clone https://github.com/aiming-lab/SimpleMem.git

# Install dependencies
cd SimpleMem
pip install -r requirements.txt

# For GPU acceleration (optional)
pip install -r requirements-gpu.txt

# Configure
cp config.py.example config.py
# Edit config.py with your API keys
```

## Appendix B: Dependencies

```
lancedb>=0.4.0
sentence-transformers>=2.2.0
pydantic>=2.0.0
pyarrow>=14.0.0
dateparser>=1.2.0
openai>=1.0.0
```

## Appendix C: License

SimpleMem is released under the MIT License.
