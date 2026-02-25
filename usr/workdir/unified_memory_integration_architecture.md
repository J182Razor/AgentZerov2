# Unified AI Memory Integration Architecture for Agent Zero

**Document Version:** 1.0 
**Created:** 2026-02-22 
**Status:** Integration Specification 

---

## Executive Summary

This document specifies the unified integration of three complementary AI memory systems into the Agent Zero framework:

| System | Primary Capability | Latency | Token Efficiency | Modality Support |
|--------|-------------------|---------|------------------|------------------|
| **memvid** | Single-file persistent storage | 0.025ms P50 | N/A | Text + CLIP embeddings |
| **SimpleMem** | Semantic compression | ~550ms/query | 98% reduction | Text only |
| **RAG-Anything** | Multimodal processing | Variable | N/A | Text + Images + Tables + Equations |

**Integration Philosophy:** Layered architecture with intelligent routing based on content type and query complexity.

---

## 1. Unified Architecture Diagram

```
+-------------------------------------------------------------------------------------+
| AGENT ZERO FRAMEWORK |
| +-------------+ +-------------+ +-------------+ +-------------+ |
| |memory_save | |memory_load | |document_ | | swarm_* | |
| | | | | |query | | patterns | |
| +------+------+ +------+------+ +------+------+ +------+------+ |
+---------+----------------+----------------+----------------+----------------------+
 | | | |
 v v v v
+-------------------------------------------------------------------------------------+
| UNIFIED MEMORY ORCHESTRATION LAYER |
| |
| +-------------------------------------------------------------------------------+ |
| | MemoryRouter (Intelligent Routing) | |
| | +-------------+ +-------------+ +-------------+ +-------------+ | |
| | | Content | | Query | | Performance | | Modality | | |
| | | Analyzer | | Classifier | | Estimator | | Detector | | |
| | +-------------+ +-------------+ +-------------+ +-------------+ | |
| +-------------------------------------------------------------------------------+ |
| |
| +---------------------+ +---------------------+ +---------------------+ |
| | INGESTION PIPELINE | | RETRIEVAL PIPELINE | | CONSOLIDATION ENGINE | |
| | | | | | | |
| | +-----------------+ | | +-----------------+ | | +-----------------+ | |
| | | Content Parser | | | | Query Planner | | | | Decay Manager | | |
| | | (RAG-Anything) | | | | (SimpleMem) | | | | (SimpleMem) | | |
| | +--------+--------+ | | +--------+--------+ | | +--------+--------+ | |
| | v | | v | | v | |
| | +-----------------+ | | +-----------------+ | | +-----------------+ | |
| | | Semantic | | | | Hybrid Search | | | | Merge Manager | | |
| | | Compressor | | | | (memvid) | | | | (SimpleMem) | | |
| | | (SimpleMem) | | | +--------+--------+ | | +--------+--------+ | |
| | +--------+--------+ | | | | | | | | |
| | v | | v | | v | |
| | +-----------------+ | | +-----------------+ | | +-----------------+ | |
| | | Persistence | | | | Result Fusion | | | | Prune Manager | | |
| | | (memvid) | | | | (All) | | | | (memvid) | | |
| | +-----------------+ | | +-----------------+ | | +-----------------+ | |
| | +---------------------+ +---------------------+ +---------------------+ |
+-------------------------------------------------------------------------------------+
 | | | |
 v v v v
+-------------------------------------------------------------------------------------+
| STORAGE BACKEND LAYER |
| |
| +-------------------------------------------------------------------------------+ |
| | memvid (.mv2 files) | |
| | +-------------+ +-------------+ +-------------+ +-------------+ | |
| | | WAL | | Lex Index | | Vec Index | | Time Index | | |
| | | (Tantivy) | | (BM25) | | (HNSW) | | (Chrono) | | |
| | +-------------+ +-------------+ +-------------+ +-------------+ | |
| +-------------------------------------------------------------------------------+ |
| |
| +-------------------------------------------------------------------------------+ |
| | SimpleMem Vector Store (LanceDB) | |
| | +-------------+ +-------------+ +-------------+ | |
| | | Semantic | | Keyword | | Structured | | |
| | | Index | | Index | | Index | | |
| | +-------------+ +-------------+ +-------------+ | |
| +-------------------------------------------------------------------------------+ |
| |
| +-------------------------------------------------------------------------------+ |
| | RAG-Anything Knowledge Graphs | |
| | +-----------------------------+ +-----------------------------+ | |
| | | Text Knowledge Graph | | Cross-Modal Graph | | |
| | | (Entity-Relationship) | | (Image-Table-Text Links) | | |
| | +-----------------------------+ +-----------------------------+ | |
| +-------------------------------------------------------------------------------+ |
+-------------------------------------------------------------------------------------+
```

### Data Flow Architecture

```
 +------------------+
 | User Content |
 | (Text/Image/ |
 | Table/Equation) |
 +-------+----------+
 |
 v
 +--------------------------------------+
 | CONTENT CLASSIFICATION |
 | +------------+ +------------+ |
 | | Modality | | Complexity | |
 | | Detection | | Analysis | |
 | +------------+ +------------+ |
 +---------------+----------------------+
 |
 +---------------------+---------------------+
 | | |
 v v v
 +----------------+ +----------------+ +----------------+
 | TEXT-ONLY | | MULTIMODAL | | HIGH-VOLUME |
 | SIMPLE QUERY | | CONTENT | | BATCH INGEST |
 +-------+--------+ +-------+--------+ +-------+--------+
 | | |
 v v v
 +----------------+ +----------------+ +----------------+
 | SimpleMem | | RAG-Anything | | memvid |
 | Pipeline | | Pipeline | | Direct Write |
 | | | | | |
 | - Compress | | - Parse Media | | - WAL Write |
 | - Multi-index | | - Extract Feat | | - Index Build |
 | - Store | | - Build Graph | | - Batch Opt |
 +-------+--------+ +-------+--------+ +-------+--------+
 | | |
 +---------------------+---------------------+
 |
 v
 +--------------------------------------+
 | UNIFIED STORAGE LAYER |
 | |
 | memvid.mv2 <--> LanceDB <--> KG Store |
 +------------------+-------------------+
 |
 v
 +--------------------------------------+
 | QUERY PROCESSING |
 | |
 | 1. Parse Intent (SimpleMem) |
 | 2. Plan Retrieval (Hybrid) |
 | 3. Execute Search (memvid+KG) |
 | 4. Fuse Results (All) |
 | 5. Generate Answer |
 +--------------------------------------+
```

---

## 2. Benefits Analysis Matrix

### Capability Comparison

| Feature | memvid | SimpleMem | RAG-Anything | Unified Integration |
|---------|--------|-----------|--------------|---------------------|
| **Storage Model** | Single-file binary | LanceDB tables | Graph + Vector | Hybrid multi-store |
| **Latency** | 0.025ms P50 | ~550ms/query | Variable | Routing-optimized |
| **Token Efficiency** | N/A | 98% reduction | N/A | Context-aware |
| **Search Quality** | BM25 + HNSW | 43.24% F1 | +13.8% long-doc | Combined best |
| **Modalities** | Text + CLIP | Text only | Text+Img+Tbl+Eq | Full multimodal |
| **Portability** | 5 stars | 3 stars | 2 stars | Layered approach |
| **Infrastructure** | None required | LanceDB | GPU optional | Configurable |
| **Compression** | Native frames | 30x semantic | N/A | Pipeline-based |
| **Indexing** | Multi-index | Multi-view | Dual-graph | Unified indices |

### Synergy Analysis

```
+---------------------------------------------------------------------------------+
| SYNERGY MATRIX |
+---------------------------------------------------------------------------------+
| |
| HIGH SYNERGY (Complementary) |
| ============================== |
| - memvid + SimpleMem: Fast storage + semantic compression = optimal memory |
| - SimpleMem + RAG-Anything: Text compression + multimodal = efficient docs |
| - memvid + RAG-Anything: Portable storage + multimodal = shareable knowledge |
| |
| MODERATE SYNERGY (Overlapping) |
| ================================ |
| - memvid <-> SimpleMem: Both provide search (unified via hybrid) |
| - SimpleMem <-> RAG-Anything: Both process text (router determines path) |
| |
| LOW SYNERGY (Redundant) |
| ======================== |
| - Vector embeddings: All three provide (standardize on one embedding model) |
| - Text search: memvid BM25 + SimpleMem keyword (merge at query time) |
| |
+---------------------------------------------------------------------------------+
```

### Use Case Decision Matrix

| Use Case | Primary System | Fallback | Rationale |
|----------|---------------|----------|-----------|
| Quick fact lookup | memvid | SimpleMem | Sub-ms latency, BM25 precision |
| Semantic search | SimpleMem | memvid | Intent-aware, multi-view indexing |
| Document Q&A | SimpleMem + RAG-Anything | memvid | Compression + multimodal extraction |
| Image content search | RAG-Anything | memvid (CLIP) | Vision encoder integration |
| Table/equation extraction | RAG-Anything | - | Specialized analyzers |
| Long-term memory consolidation | SimpleMem | memvid | Decay + merge algorithms |
| Portable knowledge transfer | memvid | - | Single-file portability |
| Real-time chat context | memvid | SimpleMem | WAL durability, low latency |
| Research paper analysis | RAG-Anything | SimpleMem | Multimodal + semantic compression |
| Enterprise knowledge base | All three | - | Full pipeline integration |

---

## 3. Integration Timeline with Swarm Protocols

### Phase 1: Core Infrastructure (Weeks 1-3)

**Objective:** Establish unified storage backend and routing foundation

**Week 1-2: memvid Integration**
- Install memvid-sdk, create .mv2 file handlers
- Implement MemvidAdapter class with CRUD operations
- Create WAL integration for durability
- Build index management (Lex, Vec, Time)

**Swarm Pattern:** swarm_sequential
```
developer[adapter] -> developer[indexer] -> developer[integration]
```

**Agent Configuration:**
- developer (adapter): Create MemvidAdapter with put/get/delete/find methods
- developer (indexer): Implement hybrid index management
- developer (integration): Wire into Agent Zero tool system

**Duration:** 10 days | **Risk:** Low | **Dependencies:** None

**Week 3: Unified Router Foundation**
- Create MemoryRouter class with content analysis
- Implement modality detection (text/image/table/equation)
- Build query complexity estimator
- Create routing decision engine

**Swarm Pattern:** swarm_concurrent
```
developer[content] developer[query] developer[routing]
 -> aggregator -> MemoryRouter
```

**Aggregation:** summary (synthesis of parallel work)
**Duration:** 5 days | **Risk:** Medium | **Dependencies:** memvid

---

### Phase 2: Semantic Layer (Weeks 4-6)

**Objective:** Integrate SimpleMem compression and retrieval

**Week 4-5: SimpleMem Core Components**
- Install LanceDB, sentence-transformers dependencies
- Implement SemanticCompressor (gate, extract, coref, time)
- Create MemoryBuilder with multi-view indexing
- Build HybridRetriever with intent planning

**Swarm Pattern:** swarm_hierarchical
```
architect (root)
 |
 +----------------+----------------+
 | | |
 v v v
compressor retriever integrator
(manager) (manager) (manager)
 | | |
 +----+----+ +----+----+ +----+----+
 | | | | | |
 v v v v v v
gate extract plan search lancedb adapters
 (w) (w) (w) (w) (w) (w)
```

**Agent Configuration:**
- architect: Design component interfaces and data contracts
- compressor manager + workers: Build compression pipeline
- retriever manager + workers: Build retrieval pipeline
- integrator manager + workers: Wire into Agent Zero

**Duration:** 10 days | **Risk:** Medium | **Dependencies:** Phase 1

**Week 6: Enhanced Memory Tools**
- Replace memory_save with memory_save_enhanced
- Replace memory_load with memory_load_enhanced
- Create memory_consolidate tool
- Implement CrossMemOrchestrator for session management

**Swarm Pattern:** swarm_graph (conditional workflow)
```
start -> analyze existing -> migrate tools -> test suite
 |
 v
 validate success?
 |
 +-------------+-------------+
 | | |
 [success] [partial] [failed]
 | | |
 v v v
 deploy fallback rollback
```

**Duration:** 5 days | **Risk:** High | **Dependencies:** SimpleMem core

---

### Phase 3: Multimodal Integration (Weeks 7-9)

**Objective:** Add RAG-Anything multimodal processing capabilities

**Week 7-8: RAG-Anything Core**
- Install raganything[all] dependencies
- Implement DocumentParser (MinerU/Docling)
- Create multimodal analyzers (Image, Table, Equation)
- Build Dual-Graph Knowledge construction
- Implement cross-modal retrieval

**Swarm Pattern:** swarm_moa (Mixture of Agents)
```
Round 1: Initial Proposals
 parser specialist | analyzer specialist | grapher specialist

Round 2: Refinement with Cross-Context
 parser refined | analyzer refined | grapher refined

Aggregation:
 senior_architect (synthesize multimodal pipeline)
```

**Rounds:** 2-3 | **Duration:** 10 days | **Risk:** High | **Dependencies:** Phase 2

**Week 9: Integration Testing**
- Wire RAG-Anything into document_query tool
- Create MultimodalMemoryAdapter
- Implement content routing based on modality
- Performance benchmarking and optimization

**Swarm Pattern:** swarm_vote (consensus testing)
```
Task: Validate multimodal integration correctness

tester_1 (image) | tester_2 (table) | tester_3 (equation) | tester_4 (hybrid)
 |
 v
 Voting Strategy: semantic | Tie-break: llm | Threshold: 0.85
 |
 v
 Consensus Result
```

**Duration:** 5 days | **Risk:** Medium | **Dependencies:** RAG-Anything core

---

### Phase 4: Production Hardening (Weeks 10-12)

**Objective:** Finalize integration, optimize performance, ensure reliability

**Week 10-11: Performance Optimization**
- Implement caching layer for frequent queries
- Optimize index merging strategies
- Add connection pooling for LanceDB
- Create async batch processing pipeline

**Swarm Pattern:** swarm_star (hub-and-spoke optimization)
```
 hub_optimizer (central)
 |
 +---------------------+---------------------+
 | | |
 v v v
cache optimizer index optimizer async optimizer
 (spoke) (spoke) (spoke)
 |
 v
 aggregation (final plan)
```

**Duration:** 10 days | **Risk:** Medium | **Dependencies:** Phase 3

**Week 12: Final Validation & Deployment**
- End-to-end integration testing
- Documentation completion
- Migration guide creation
- Production deployment and monitoring setup

**Swarm Pattern:** swarm_concurrent + swarm_vote (final validation)

**Duration:** 5 days | **Risk:** Low | **Dependencies:** Optimization complete

---

## 4. Implementation Priority Ranking

### Priority Matrix

**PRIORITY 1: memvid Integration (CRITICAL PATH)**
- **Justification:** Foundation layer for all storage operations
- **Benefits:**
  - Immediate sub-millisecond latency improvement
  - Zero infrastructure requirements
  - Single-file portability for knowledge transfer
  - WAL durability for crash recovery
- **Dependencies:** None
- **Risk:** Low - mature SDK, well-documented API
- **Duration:** 10 days
- **Blocking:** Phase 2, Phase 3

**PRIORITY 2: SimpleMem Integration (HIGH VALUE)**
- **Justification:** Core intelligence layer for semantic operations
- **Benefits:**
  - 98% token reduction for context efficiency
  - 30x inference cost reduction
  - Intent-aware retrieval improves relevance
  - Cross-session memory continuity
- **Dependencies:** memvid (storage backend)
- **Risk:** Medium - complex pipeline, LanceDB integration
- **Duration:** 15 days
- **Blocking:** Phase 3 (multimodal text processing)

**PRIORITY 3: RAG-Anything Integration (ENHANCEMENT)**
- **Justification:** Multimodal capability expansion
- **Benefits:**
  - Process images, tables, equations
  - +13.8% improvement on long documents
  - Cross-modal knowledge graph
- **Dependencies:** memvid + SimpleMem (routing foundation)
- **Risk:** High - GPU optional, complex parsing
- **Duration:** 15 days
- **Blocking:** None (optional enhancement)

### Dependency Graph

```
 +-----------------+
 | START |
 +--------+--------+
 |
 v
 +-----------------+
 | memvid | <--- PRIORITY 1
 | (10 days) | Foundation
 +--------+--------+
 |
 +--------------+--------------+
 | |
 v v
 +-----------------+ +-----------------+
 | SimpleMem | | Router Core |
 | (15 days) |<----+---->| (5 days) |
 | PRIORITY 2 | |
 +--------+--------+ +--------+--------+
 | |
 +--------------+--------------+
 |
 v
 +-----------------+
 | RAG-Anything | <--- PRIORITY 3
 | (15 days) | Enhancement
 +--------+--------+
 |
 v
 +-----------------+
 | Optimization |
 | & Hardening |
 +--------+--------+
 |
 v
 +-----------------+
 | COMPLETE |
 +-----------------+
```

### Risk Assessment

| Risk Category | memvid | SimpleMem | RAG-Anything | Mitigation |
|---------------|--------|-----------|--------------|------------|
| **Technical Complexity** | Low | Medium | High | Phased rollout, fallback mechanisms |
| **Integration Effort** | Low | Medium | High | Swarm patterns for parallel development |
| **Performance Impact** | Positive | Mixed | Variable | Benchmarking at each phase |
| **Dependency Risk** | Low | Medium | High | Version pinning, container isolation |
| **Rollback Complexity** | Low | Medium | High | Feature flags, gradual migration |
| **Testing Coverage** | High | Medium | Low | Automated test suites per component |

---

## 5. API Design

### 5.1 Enhanced Memory Save Tool

```python
# python/tools/memory_save_enhanced.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class ContentType(Enum):
 TEXT = "text"
 IMAGE = "image"
 TABLE = "table"
 EQUATION = "equation"
 MIXED = "mixed"


@dataclass
class MemorySaveConfig:
 """Configuration for enhanced memory save operations."""
 
 # Compression settings
 enable_compression: bool = True
 compression_level: Literal["fast", "balanced", "deep"] = "balanced"
 
 # Indexing settings
 enable_semantic_index: bool = True
 enable_keyword_index: bool = True
 enable_temporal_index: bool = True
 
 # Multimodal settings
 extract_images: bool = True
 extract_tables: bool = True
 extract_equations: bool = True
 
 # Storage settings
 storage_backend: Literal["memvid", "lancedb", "auto"] = "auto"
 
 # Metadata
 tags: List[str] = None
 source: Optional[str] = None
 importance: float = 0.5
 ttl_days: Optional[int] = None


@dataclass
class MemorySaveResult:
 """Result of enhanced memory save operation."""
 
 success: bool
 memory_id: str
 storage_location: str
 tokens_saved: int
 compression_ratio: float
 indices_created: List[str]
 modalities_detected: List[ContentType]
 processing_time_ms: float
 error: Optional[str] = None


class MemorySaveEnhanced:
 """
 Enhanced memory save tool integrating memvid, SimpleMem, and RAG-Anything.
 
 Routing Logic:
 1. Analyze content type and complexity
 2. Route to appropriate pipeline:
 - Text-only simple: SimpleMem compression -> memvid storage
 - Multimodal: RAG-Anything extraction -> memvid storage
 - High-volume batch: Direct memvid write with batch optimization
 3. Return memory ID with metadata
 """
 
 def __init__(self, config: Optional[MemorySaveConfig] = None):
 self.config = config or MemorySaveConfig()
 self.router = MemoryRouter()
 self.memvid_adapter = MemvidAdapter()
 self.simplemem_pipeline = SimpleMemPipeline()
 self.rag_anything_processor = RAGAnythingProcessor()
 
 async def execute(
 self,
 text: str,
 metadata: Optional[Dict[str, Any]] = None,
 attachments: Optional[List[str]] = None,
 config_override: Optional[MemorySaveConfig] = None
 ) -> MemorySaveResult:
 """
 Save content to unified memory system.
 
 Args:
 text: Primary text content to store
 metadata: Optional metadata dictionary
 attachments: Optional list of file paths (images, PDFs, etc.)
 config_override: Override default configuration
 
 Returns:
 MemorySaveResult with operation details
 """
 config = config_override or self.config
 
 # Step 1: Analyze content
 content_analysis = await self.router.analyze_content(text, attachments)
 
 # Step 2: Route to appropriate pipeline
 if content_analysis.modality == ContentType.TEXT and not attachments:
 # Text-only: Use SimpleMem compression
 compressed = await self.simplemem_pipeline.compress(text, config)
 storage_result = await self.memvid_adapter.store(
 content=compressed.content,
 embedding=compressed.embedding,
 metadata=metadata,
 indices=["semantic", "keyword", "temporal"]
 )
 
 elif content_analysis.modality in [ContentType.IMAGE, ContentType.TABLE, ContentType.EQUATION, ContentType.MIXED]:
 # Multimodal: Use RAG-Anything
 processed = await self.rag_anything_processor.process(
 text=text,
 attachments=attachments,
 config=config
 )
 storage_result = await self.memvid_adapter.store(
 content=processed.text,
 embedding=processed.embedding,
 metadata={**metadata, "multimodal": processed.modality_metadata},
 indices=["semantic", "keyword", "temporal", "visual"]
 )
 
 else:
 # Fallback: Direct memvid write
 storage_result = await self.memvid_adapter.store(
 content=text,
 metadata=metadata
 )
 
 return MemorySaveResult(
 success=True,
 memory_id=storage_result.id,
 storage_location=storage_result.location,
 tokens_saved=content_analysis.original_tokens - content_analysis.final_tokens,
 compression_ratio=content_analysis.compression_ratio,
 indices_created=storage_result.indices,
 modalities_detected=[content_analysis.modality],
 processing_time_ms=storage_result.time_ms
 )
```

### 5.2 Enhanced Memory Load Tool

```python
# python/tools/memory_load_enhanced.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import asyncio


class SearchMode(Enum):
 SEMANTIC = "semantic" # Vector similarity
 KEYWORD = "keyword" # BM25 full-text
 HYBRID = "hybrid" # Combined semantic + keyword
 GRAPH = "graph" # Knowledge graph traversal
 MULTIMODAL = "multimodal" # Cross-modal search


@dataclass
class MemoryLoadConfig:
 """Configuration for enhanced memory load operations."""
 
 # Search settings
 mode: SearchMode = SearchMode.HYBRID
 top_k: int = 10
 min_score: float = 0.5
 
 # Semantic search settings
 semantic_weight: float = 0.6
 keyword_weight: float = 0.3
 graph_weight: float = 0.1
 
 # Intent-aware settings
 enable_intent_planning: bool = True
 enable_reflection: bool = True
 reflection_iterations: int = 2
 
 # Cross-modal settings
 include_images: bool = True
 include_tables: bool = True
 include_equations: bool = True
 
 # Performance settings
 timeout_ms: int = 5000
 cache_results: bool = True
 cache_ttl_seconds: int = 300


@dataclass
class MemorySearchResult:
 """Individual search result item."""
 
 memory_id: str
 score: float
 content: str
 metadata: Dict[str, Any]
 source_components: List[str] # Which indices contributed
 modalities: List[str]
 timestamp: str


@dataclass
class MemoryLoadResult:
 """Result of enhanced memory load operation."""
 
 success: bool
 results: List[MemorySearchResult]
 query_intent: str
 total_tokens_used: int
 search_time_ms: float
 indices_queried: List[str]
 reflection_notes: Optional[List[str]] = None
 error: Optional[str] = None


class MemoryLoadEnhanced:
 """
 Enhanced memory load tool with hybrid search capabilities.
 
 Search Flow:
 1. Intent Planning (SimpleMem): Analyze query to determine search strategy
 2. Multi-Index Search (memvid): Query semantic, keyword, temporal indices
 3. Graph Traversal (RAG-Anything): Cross-modal knowledge graph lookup
 4. Result Fusion: Combine and rank results from all sources
 5. Reflection: Refine query if results are unsatisfactory
 """
 
 def __init__(self, config: Optional[MemoryLoadConfig] = None):
 self.config = config or MemoryLoadConfig()
 self.intent_planner = IntentPlanner()
 self.memvid_searcher = MemvidHybridSearcher()
 self.graph_searcher = KnowledgeGraphSearcher()
 self.result_fuser = ResultFuser()
 
 async def execute(
 self,
 query: str,
 threshold: float = 0.7,
 limit: int = 5,
 filter: Optional[str] = None,
 config_override: Optional[MemoryLoadConfig] = None
 ) -> MemoryLoadResult:
 """
 Search unified memory system with intelligent query planning.
 
 Args:
 query: Search query text
 threshold: Minimum relevance threshold (0-1)
 limit: Maximum number of results
 filter: Optional Python filter expression
 config_override: Override default configuration
 
 Returns:
 MemoryLoadResult with ranked search results
 """
 config = config_override or self.config
 config.top_k = limit
 config.min_score = threshold
 
 # Step 1: Intent Planning
 if config.enable_intent_planning:
 intent_plan = await self.intent_planner.plan(query)
 search_strategy = intent_plan.strategy
 else:
 search_strategy = SearchStrategy(config.mode)
 
 # Step 2: Execute Multi-Source Search
 search_tasks = []
 
 # Semantic search
 if search_strategy.include_semantic:
 search_tasks.append(self.memvid_searcher.semantic_search(query, config.top_k))
 
 # Keyword search
 if search_strategy.include_keyword:
 search_tasks.append(self.memvid_searcher.keyword_search(query, config.top_k))
 
 # Graph search (for multimodal queries)
 if search_strategy.include_graph and config.mode == SearchMode.MULTIMODAL:
 search_tasks.append(self.graph_searcher.search(query, config.top_k))
 
 # Execute all searches in parallel
 search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
 
 # Step 3: Fuse Results
 fused_results = await self.result_fuser.fuse(
 results=search_results,
 weights={
 "semantic": config.semantic_weight,
 "keyword": config.keyword_weight,
 "graph": config.graph_weight
 },
 min_score=config.min_score
 )
 
 # Step 4: Reflection (if enabled and results unsatisfactory)
 reflection_notes = []
 if config.enable_reflection and len(fused_results) < limit:
 for iteration in range(config.reflection_iterations):
 refined_query = await self.intent_planner.reflect(query, fused_results)
 reflection_notes.append(f"Iteration {iteration + 1}: {refined_query.rationale}")
 
 # Re-search with refined query
 additional_results = await self._execute_search(refined_query.query, config)
 fused_results = self._merge_results(fused_results, additional_results)
 
 return MemoryLoadResult(
 success=True,
 results=fused_results[:limit],
 query_intent=intent_plan.intent if config.enable_intent_planning else "unknown",
 total_tokens_used=sum(r.tokens for r in fused_results),
 search_time_ms=sum(r.time_ms for r in search_results),
 indices_queried=search_strategy.indices,
 reflection_notes=reflection_notes if reflection_notes else None
 )
```

### 5.3 Memory Consolidation Tool

```python
# python/tools/memory_consolidate.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


@dataclass
class ConsolidationConfig:
 """Configuration for memory consolidation operations."""
 
 # Decay settings
 enable_decay: bool = True
 decay_factor: float = 0.9
 decay_age_days: int = 30
 
 # Merge settings
 enable_merge: bool = True
 merge_threshold: float = 0.95 # Cosine similarity threshold
 
 # Prune settings
 enable_prune: bool = True
 min_importance: float = 0.05
 max_age_days: int = 90
 
 # Safety settings
 dry_run: bool = False
 backup_before_consolidate: bool = True
 preserve_tagged: List[str] = None # Tags to preserve regardless of decay


@dataclass
class ConsolidationStats:
 """Statistics from consolidation operation."""
 
 memories_before: int
 memories_after: int
 decayed_count: int
 merged_count: int
 pruned_count: int
 space_saved_bytes: int
 processing_time_ms: float
 backup_location: Optional[str]


@dataclass
class ConsolidationResult:
 """Result of memory consolidation operation."""
 
 success: bool
 stats: ConsolidationStats
 changes: List[Dict[str, Any]] # Detailed change log
 error: Optional[str] = None


class MemoryConsolidate:
 """
 Memory consolidation tool for lifelong memory maintenance.
 
 Consolidation Pipeline:
 1. Backup: Create snapshot before changes
 2. Decay: Reduce importance of aged memories
 3. Merge: Combine near-duplicate memories
 4. Prune: Remove low-importance memories
 5. Reindex: Update indices after consolidation
 """
 
 def __init__(self, config: Optional[ConsolidationConfig] = None):
 self.config = config or ConsolidationConfig()
 self.memvid_manager = MemvidManager()
 self.simplemem_consolidator = SimpleMemConsolidator()
 
 async def execute(
 self,
 scope: str = "all", # "all", "text", "multimodal", "aged"
 config_override: Optional[ConsolidationConfig] = None
 ) -> ConsolidationResult:
 """
 Execute memory consolidation to optimize storage and retrieval.
 
 Args:
 scope: Scope of consolidation
 config_override: Override default configuration
 
 Returns:
 ConsolidationResult with operation statistics
 """
 config = config_override or self.config
 changes = []
 
 # Step 1: Backup (if enabled)
 backup_location = None
 if config.backup_before_consolidate and not config.dry_run:
 backup_location = await self.memvid_manager.create_backup()
 
 # Get initial count
 stats_before = await self.memvid_manager.get_stats()
 
 # Step 2: Decay aged memories
 decayed_count = 0
 if config.enable_decay:
 decay_result = await self.simplemem_consolidator.apply_decay(
 decay_factor=config.decay_factor,
 age_threshold_days=config.decay_age_days,
 preserve_tagged=config.preserve_tagged,
 dry_run=config.dry_run
 )
 decayed_count = decay_result.count
 changes.extend(decay_result.changes)
 
 # Step 3: Merge near-duplicates
 merged_count = 0
 if config.enable_merge:
 merge_result = await self.simplemem_consolidator.merge_duplicates(
 similarity_threshold=config.merge_threshold,
 scope=scope,
 dry_run=config.dry_run
 )
 merged_count = merge_result.count
 changes.extend(merge_result.changes)
 
 # Step 4: Prune low-importance
 pruned_count = 0
 if config.enable_prune:
 prune_result = await self.simplemem_consolidator.prune(
 min_importance=config.min_importance,
 max_age_days=config.max_age_days,
 preserve_tagged=config.preserve_tagged,
 dry_run=config.dry_run
 )
 pruned_count = prune_result.count
 changes.extend(prune_result.changes)
 
 # Get final count
 stats_after = await self.memvid_manager.get_stats()
 
 return ConsolidationResult(
 success=True,
 stats=ConsolidationStats(
 memories_before=stats_before.total_memories,
 memories_after=stats_after.total_memories if not config.dry_run else stats_before.total_memories,
 decayed_count=decayed_count,
 merged_count=merged_count,
 pruned_count=pruned_count,
 space_saved_bytes=stats_before.size_bytes - stats_after.size_bytes,
 processing_time_ms=stats_after.processing_time_ms,
 backup_location=backup_location
 ),
 changes=changes
 )
```

### 5.4 Configuration Options

```yaml
# config/memory_integration.yaml

# Unified Memory System Configuration
memory:
 # Global settings
 enabled: true
 default_backend: "auto" # "memvid", "lancedb", "auto"
 
 # Router configuration
 router:
 complexity_threshold: 0.5
 modality_detection: true
 performance_estimation: true
 
 # memvid settings
 memvid:
 data_dir: "/a0/usr/workdir/memvid"
 default_file: "knowledge.mv2"
 index_config:
 lex: true # BM25 full-text
 vec: true # HNSW vector
 time: true # Temporal
 clip: false # CLIP visual (requires GPU)
 wal:
 enabled: true
 max_size_mb: 64
 encryption:
 enabled: false
 # password: set via environment variable
 
 # SimpleMem settings
 simplemem:
 compression:
 enabled: true
 level: "balanced" # "fast", "balanced", "deep"
 window_size: 40
 overlap_size: 2
 
 indexing:
 semantic: true
 keyword: true
 structured: true
 
 retrieval:
 semantic_top_k: 25
 keyword_top_k: 5
 enable_reflection: true
 reflection_iterations: 2
 
 consolidation:
 auto_consolidate: true
 schedule: "0 3 * * *" # Daily at 3 AM
 decay_factor: 0.9
 decay_age_days: 30
 merge_threshold: 0.95
 prune_min_importance: 0.05
 
 # RAG-Anything settings
 rag_anything:
 enabled: true
 data_dir: "/a0/usr/workdir/rag_storage"
 
 parser:
 backend: "mineru" # "mineru", "docling"
 method: "auto"
 
 modalities:
 image: true
 table: true
 equation: true
 
 knowledge_graph:
 enabled: true
 text_graph: true
 cross_modal_graph: true
 
 performance:
 device: "cuda" # "cuda", "cpu"
 max_concurrent_files: 1
 context_window: 1
 max_context_tokens: 2000
 
 # Caching settings
 cache:
 enabled: true
 ttl_seconds: 300
 max_size_mb: 100
 
 # Fallback settings
 fallback:
 enabled: true
 primary_backend: "memvid"
 fallback_backend: "lancedb"
 timeout_ms: 5000

# Environment variable overrides
# MEMORY_ENABLED=true
# MEMORY_DEFAULT_BACKEND=memvid
# MEMVID_DATA_DIR=/a0/usr/workdir/memvid
# SIMPLEMEM_COMPRESSION_ENABLED=true
# RAG_ANYTHING_DEVICE=cuda
```

### 5.5 Fallback Mechanisms

```python
# python/helpers/memory_fallback.py

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum
import asyncio


class FallbackReason(Enum):
 TIMEOUT = "timeout"
 ERROR = "error"
 UNAVAILABLE = "unavailable"
 PERFORMANCE = "performance"


@dataclass
class FallbackResult:
 """Result from fallback operation."""
 success: bool
 result: Any
 used_fallback: bool
 reason: Optional[FallbackReason]
 original_backend: str
 fallback_backend: str


class MemoryFallbackHandler:
 """
 Handles graceful degradation between memory backends.
 
 Fallback Chain:
 1. Primary (memvid) -> Fast, portable, durable
 2. Secondary (LanceDB/SimpleMem) -> Semantic, compressible
 3. Tertiary (in-memory cache) -> Ultra-fast, volatile
 """
 
 def __init__(self, config: dict):
 self.primary = MemvidAdapter(config.get("memvid", {}))
 self.secondary = LanceDBAdapter(config.get("simplemem", {}))
 self.tertiary = InMemoryCache(config.get("cache", {}))
 self.timeout_ms = config.get("fallback", {}).get("timeout_ms", 5000)
 
 async def save_with_fallback(
 self,
 content: str,
 metadata: dict,
 preferred_backend: str = "auto"
 ) -> FallbackResult:
 """Execute save with automatic fallback on failure."""
 
 backends = self._get_backend_chain(preferred_backend)
 
 for backend_name, backend in backends:
 try:
 result = await asyncio.wait_for(
 backend.save(content, metadata),
 timeout=self.timeout_ms / 1000
 )
 return FallbackResult(
 success=True,
 result=result,
 used_fallback=(backend_name != backends[0][0]),
 reason=None,
 original_backend=backends[0][0],
 fallback_backend=backend_name if backend_name != backends[0][0] else None
 )
 except asyncio.TimeoutError:
 continue
 except Exception:
 continue
 
 # All backends failed
 return FallbackResult(
 success=False,
 result=None,
 used_fallback=True,
 reason=FallbackReason.ERROR,
 original_backend=backends[0][0],
 fallback_backend=None
 )
 
 async def load_with_fallback(
 self,
 query: str,
 limit: int = 5,
 preferred_backend: str = "auto"
 ) -> FallbackResult:
 """Execute load with automatic fallback on failure."""
 
 backends = self._get_backend_chain(preferred_backend)
 
 for backend_name, backend in backends:
 try:
 result = await asyncio.wait_for(
 backend.search(query, limit),
 timeout=self.timeout_ms / 1000
 )
 return FallbackResult(
 success=True,
 result=result,
 used_fallback=(backend_name != backends[0][0]),
 reason=None,
 original_backend=backends[0][0],
 fallback_backend=backend_name if backend_name != backends[0][0] else None
 )
 except asyncio.TimeoutError:
 continue
 except Exception:
 continue
 
 return FallbackResult(
 success=False,
 result=None,
 used_fallback=True,
 reason=FallbackReason.ERROR,
 original_backend=backends[0][0],
 fallback_backend=None
 )
 
 def _get_backend_chain(self, preferred: str) -> list:
 """Get ordered list of backends to try."""
 if preferred == "memvid":
 return [("memvid", self.primary), ("lancedb", self.secondary), ("cache", self.tertiary)]
 elif preferred == "lancedb":
 return [("lancedb", self.secondary), ("memvid", self.primary), ("cache", self.tertiary)]
 else: # auto
 return [("memvid", self.primary), ("lancedb", self.secondary), ("cache", self.tertiary)]
```

---

## Summary

This unified integration architecture provides Agent Zero with a comprehensive memory system that combines:

1. **memvid**: Lightning-fast, portable, single-file storage with WAL durability
2. **SimpleMem**: 98% token reduction through semantic compression
3. **RAG-Anything**: Full multimodal processing for images, tables, and equations

### Key Benefits

| Metric | Improvement |
|--------|-------------|
| Query Latency | 0.025ms P50 (memvid) |
| Token Efficiency | 98% reduction (SimpleMem) |
| Long Document Accuracy | +13.8% (RAG-Anything) |
| Inference Cost | 30x reduction (SimpleMem) |
| Portability | Single-file knowledge transfer (memvid) |

### Implementation Timeline

- **Total Duration**: 12 weeks
- **Phase 1**: 3 weeks (memvid + router)
- **Phase 2**: 3 weeks (SimpleMem)
- **Phase 3**: 3 weeks (RAG-Anything)
- **Phase 4**: 3 weeks (hardening)

### Swarm Pattern Usage Summary

| Phase | Swarm Pattern | Purpose |
|-------|---------------|---------|
| Phase 1 | swarm_sequential | Linear adapter -> indexer -> integration |
| Phase 1 | swarm_concurrent | Parallel component development |
| Phase 2 | swarm_hierarchical | Multi-level decomposition |
| Phase 2 | swarm_graph | Conditional migration workflow |
| Phase 3 | swarm_moa | Multi-round refinement with aggregation |
| Phase 3 | swarm_vote | Consensus validation |
| Phase 4 | swarm_star | Hub-and-spoke optimization |
| Phase 4 | swarm_concurrent + swarm_vote | Final validation |

### Next Steps

1. Review and approve integration specification
2. Set up development environment with dependencies
3. Begin Phase 1 with swarm_sequential pattern
4. Iterate through phases with appropriate swarm patterns
5. Validate with swarm_vote consensus testing at each phase

---

**Document Status:** Ready for Development Team Review 
**Estimated Effort:** 12 weeks, 3-4 developers 
**Risk Level:** Medium (mitigated by phased approach and fallback mechanisms)
