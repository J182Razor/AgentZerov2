# RAG-Anything Integration Specification for Agent Zero

## Executive Summary

**RAG-Anything** is an All-in-One Multimodal RAG Framework developed by HKUDS that extends traditional text-focused RAG systems to seamlessly handle diverse content modalities including text, images, tables, equations, and charts. This specification provides a comprehensive analysis and integration strategy for adding multimodal RAG capabilities to Agent Zero's document_query tool.

### Key Performance Metrics

| Benchmark | RAG-Anything | MMGraphRAG | LightRAG | GPT-4o-mini |
|-----------|--------------|------------|----------|-------------|
| DocBench (Overall) | **63.4%** | 61.0% | 58.4% | 51.2% |
| MMLongBench (Overall) | **42.8%** | 37.7% | 38.9% | 33.5% |
| Long Documents (200+ pages) | **68.8%** | 55.0% | - | - |

**Performance Advantage**: RAG-Anything shows increasing performance gaps for longer documents (>13 points for 100+ pages), making it ideal for complex technical documentation, research papers, and financial reports.

---

## 1. Architecture Overview

### 1.1 Multi-Stage Multimodal Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG-Anything Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   Document   │───▶│   Content    │───▶│  Knowledge   │───▶│ Intelligent│ │
│  │   Parsing    │    │   Analysis   │    │    Graph     │    │  Retrieval │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│         │                   │                   │                   │      │
│         ▼                   ▼                   ▼                   ▼      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   MinerU/    │    │  Specialized │    │  Dual-Graph  │    │  Vector +  │ │
│  │   Docling    │    │  Processors  │    │  Construction│    │   Graph    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Components

| Stage | Component | Description |
|-------|-----------|-------------|
| **1. Document Parsing** | MinerU / Docling Parser | High-fidelity document extraction with adaptive content decomposition |
| **2. Content Processing** | Autonomous Categorization | Routes content through optimized channels (text, image, table, equation) |
| **3. Multimodal Analysis** | Specialized Analyzers | Modality-aware processing units for heterogeneous data |
| **4. Knowledge Graph** | Dual-Graph Construction | Text-based + Cross-modal knowledge graphs with entity extraction |
| **5. Retrieval** | Vector-Graph Fusion | Combines vector similarity with graph traversal for comprehensive retrieval |

### 1.3 Knowledge Graph Architecture

```python
# Dual-Graph Structure
┌─────────────────────────────────────────────────┐
│              Text Knowledge Graph               │
│  - Entity extraction from text chunks          │
│  - Relationship inference                      │
│  - Hierarchical structure preservation         │
└─────────────────────────────────────────────────┘
                      │
                      │ Cross-modal relationships
                      ▼
┌─────────────────────────────────────────────────┐
│         Cross-Modal Knowledge Graph             │
│  - Images → Entities with visual descriptions  │
│  - Tables → Entities with statistical patterns │
│  - Equations → Entities with symbolic repr.    │
│  - "belongs_to" relationship chains             │
└─────────────────────────────────────────────────┘
```

---

## 2. Multimodal Processing Pipeline

### 2.1 Supported Content Types

| Modality | Input Formats | Processing Method | Output |
|----------|---------------|-------------------|--------|
| **Text** | Plain text, paragraphs, lists | Semantic chunking, entity extraction | Text chunks + entities |
| **Images** | JPG, PNG, BMP, TIFF, GIF, WebP | Vision model captioning (GPT-4o) | Descriptive entities |
| **Tables** | Extracted table structures | Statistical pattern recognition | Structured entities |
| **Equations** | LaTeX expressions | Symbolic representation | Mathematical entities |
| **Generic** | Custom content types | Extensible handler | Custom entities |

### 2.2 Document Format Support

```python
SUPPORTED_FORMATS = {
    "pdf": [".pdf"],                          # Research papers, reports
    "images": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"],
    "office": [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"],  # Requires LibreOffice
    "text": [".txt", ".md"],
}
```

### 2.3 Context Extraction System

RAG-Anything implements a sophisticated context extraction mechanism that preserves document structure:

```python
ContextConfig(
    context_window=1,           # Pages/chunks before and after current item
    context_mode="page",        # "page" or "chunk" based extraction
    max_context_tokens=2000,     # Maximum context token limit
    include_headers=True,        # Include document headers/titles
    include_captions=True,       # Include image/table captions
    filter_content_types=["text"]  # Content types to include in context
)
```

---

## 3. Vision Encoder Integration

### 3.1 Vision Model Architecture

RAG-Anything supports flexible vision model integration through a callable interface:

```python
def vision_model_func(
    prompt: str,
    system_prompt: str = None,
    history_messages: List[Dict] = None,
    image_data: str = None,  # Base64 encoded image
    messages: List[Dict] = None,  # For VLM-enhanced queries
    **kwargs
) -> str:
    """
    Vision model function for image analysis.
    
    Supports two modes:
    1. Single image: image_data parameter with base64
    2. Multimodal VLM: messages format with interleaved text/images
    """
    pass
```

### 3.2 Supported Vision Models

| Model | Best For | API Provider |
|-------|----------|-------------|
| **GPT-4o** | General image understanding, diagrams, charts | OpenAI |
| **GPT-4o-mini** | Cost-effective image analysis | OpenAI |
| **Claude 3.5 Sonnet** | Complex visual reasoning | Anthropic |
| **Gemini Pro Vision** | Document screenshots, handwriting | Google |
| **LLaVA** | Local/open-source option | Self-hosted |

### 3.3 Image Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Image Processing Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Extract │───▶│  Encode  │───▶│  Vision  │───▶│  Create  │  │
│  │  Image   │    │  Base64  │    │  Model   │    │  Entity  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  MinerU  │    │  PIL/    │    │  GPT-4o  │    │  Graph   │  │
│  │  Parser  │    │  Base64  │    │  API     │    │  Node    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 VLM-Enhanced Query Mode

When documents contain images, RAG-Anything can automatically:
1. Retrieve relevant context containing image paths
2. Load and encode images as base64
3. Send both text context and images to VLM for comprehensive analysis

```python
# VLM-Enhanced Query Example
result = await rag.aquery(
    "What does the architecture diagram show?",
    mode="hybrid",
    vlm_enhanced=True  # Automatically processes images in retrieved context
)
```

---

## 4. Document Parsing Capabilities

### 4.1 MinerU Parser (Primary)

MinerU provides high-fidelity document extraction with GPU acceleration support:

```python
# MinerU Configuration Options
MinerUConfig(
    parse_method="auto",       # "auto", "ocr", "txt"
    device="cuda:0",          # "cpu", "cuda", "mps", "npu"
    languages=["en", "ch"],   # OCR language optimization
    start_page=None,           # Optional page range
    end_page=None,
    enable_formula=True,       # Parse mathematical formulas
    enable_table=True,         # Parse tables
    backend="pipeline"         # "pipeline", "hybrid-auto-engine", "vlm-auto-engine"
)
```

**MinerU Capabilities:**
- OCR with multi-language support
- Table structure extraction
- Formula parsing (LaTeX)
- Image extraction with metadata
- GPU acceleration for faster processing

### 4.2 Docling Parser (Alternative)

Docling is optimized for Office documents and HTML:

```python
# Docling Configuration
DoclingConfig(
    # Better for:
    # - Office documents (.doc, .docx, .ppt, .pptx)
    # - HTML files
    # - Better document structure preservation
)
```

### 4.3 Direct Content Insertion

Bypass document parsing for pre-processed content:

```python
# Insert pre-parsed content directly
await rag.insert_content_list(
    content_list=[
        {
            "type": "text",
            "text": "Introduction paragraph...",
            "page_idx": 0
        },
        {
            "type": "image",
            "img_path": "/path/to/image.png",
            "image_caption": ["Figure 1: Architecture"],
            "page_idx": 0
        },
        {
            "type": "table",
            "table_body": "Name,Value\nAlpha,1.0\nBeta,2.0",
            "table_caption": ["Table 1: Parameters"],
            "page_idx": 1
        },
        {
            "type": "equation",
            "latex": "E = mc^2",
            "equation_caption": "Mass-energy equivalence",
            "page_idx": 1
        }
    ],
    file_path="document.pdf"
)
```

---

## 5. Cross-Modal Retrieval Mechanism

### 5.1 Dual Retrieval Strategy

RAG-Anything combines two retrieval approaches:

#### 5.1.1 Vector Similarity Search

```python
# Vector search across all modalities
┌─────────────────────────────────────────────────────┐
│                Vector Database (VDB)                │
├─────────────────────────────────────────────────────┤
│  chunks_vdb     │ Text chunks with embeddings      │
│  entities_vdb   │ Entities with descriptions      │
│  relationships  │ Relationships with keywords     │
└─────────────────────────────────────────────────────┘
```

#### 5.1.2 Graph Traversal

```python
# Knowledge graph navigation
┌─────────────────────────────────────────────────────┐
│              Knowledge Graph Operations             │
├─────────────────────────────────────────────────────┤
│  Node types:    │ text_entity, image_entity, etc.  │
│  Edge types:    │ relates_to, belongs_to, contains │
│  Traversal:     │ Multi-hop relationship following │
│  Scoring:       │ Weighted relationship relevance  │
└─────────────────────────────────────────────────────┘
```

### 5.2 Query Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `local` | Low-level entity retrieval | Specific facts, details |
| `global` | High-level concept retrieval | Overview, summaries |
| `hybrid` | Combines local + global | Balanced queries |
| `mix` | Smart mode selection | General purpose |
| `naive` | Simple chunk retrieval | Quick searches |
| `bypass` | Direct LLM without RAG | General knowledge |

### 5.3 Retrieval Configuration

```python
# LightRAG retrieval parameters
retrieval_config = {
    "top_k": 60,                    # Top entities to retrieve
    "chunk_top_k": 5,               # Top chunks per entity
    "max_entity_tokens": 20000,     # Token limit for entities
    "max_relation_tokens": 20000,   # Token limit for relations
    "max_total_tokens": 32000,      # Total context token limit
    "cosine_threshold": 0.2,        # Similarity threshold
    "related_chunk_number": 5,      # Chunks per related entity
}
```

---

## 6. Chunking Strategies for Multimodal Content

### 6.1 Adaptive Chunking Approach

RAG-Anything uses content-aware chunking that respects document structure:

```python
# Chunking Configuration
ChunkingConfig(
    chunk_token_size=1200,          # Target tokens per chunk
    chunk_overlap_token_size=100,   # Overlap between chunks
    tokenizer="tiktoken",           # Tokenizer backend
    tiktoken_model_name="gpt-4",    # Model for tokenization
)
```

### 6.2 Modality-Specific Chunking

```
┌─────────────────────────────────────────────────────────────────┐
│              Multimodal Chunking Strategy                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Text Chunks:                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Paragraph/list item boundaries                          │    │
│  │ Semantic coherence preservation                         │    │
│  │ Header hierarchy maintained                             │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Image Chunks:                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Single image = single entity                            │    │
│  │ Caption + context integrated                            │    │
│  │ Visual description generated via VLM                    │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Table Chunks:                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Complete table = single entity                          │    │
│  │ Statistical patterns extracted                          │    │
│  │ Semantic description generated                          │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Equation Chunks:                                               │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ LaTeX preserved as symbolic representation              │    │
│  │ Mathematical context included                           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Context Window Preservation

```python
def extract_context_for_chunk(
    content_list: List[Dict],
    current_chunk_idx: int,
    window_size: int = 1
) -> str:
    """
    Extract surrounding context for better understanding.
    
    Example:
    - Current chunk is on page 5
    - Window size = 1
    - Returns context from pages 4, 5, 6
    """
    pass
```

---

## 7. Hardware Requirements and Dependencies

### 7.1 System Requirements

| Component | Minimum | Recommended | High-Performance |
|-----------|---------|-------------|------------------|
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **RAM** | 8 GB | 16 GB | 32+ GB |
| **GPU** | None (CPU mode) | NVIDIA 8GB VRAM | NVIDIA 24GB+ VRAM |
| **Storage** | 10 GB | 50 GB | 500+ GB SSD |

### 7.2 GPU Requirements by Workload

| Use Case | GPU Recommendation | VRAM |
|----------|-------------------|------|
| Light documents (<50 pages) | CPU or any GPU | 4GB+ |
| Medium documents (50-200 pages) | RTX 3060/4060 | 8GB+ |
| Large documents (200+ pages) | RTX 3080/4080 | 16GB+ |
| Batch processing | RTX 4090 / A100 | 24GB+ |

### 7.3 Core Dependencies

```python
# requirements.txt
core_dependencies = [
    "lightrag-hku",           # Base RAG framework
    "mineru[core]",           # Document parsing (primary)
    "huggingface_hub",        # Model hub access
    "tqdm",                   # Progress bars
]

# Optional dependencies
optional_dependencies = {
    "image": ["Pillow>=10.0.0"],      # Image format conversion
    "text": ["reportlab>=4.0.0"],     # TXT/MD to PDF conversion
    "office": [],                      # Requires LibreOffice (external)
    "markdown": [
        "markdown>=3.4.0",
        "weasyprint>=60.0",
        "pygments>=2.10.0",
    ],
}
```

### 7.4 External Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| **LibreOffice** | Office document processing | `apt-get install libreoffice` |
| **Tesseract** | OCR (via MinerU) | Bundled with MinerU |
| **CUDA Toolkit** | GPU acceleration | NVIDIA driver + toolkit |

### 7.5 Memory Footprint Estimation

```python
def estimate_memory_requirements(
    num_documents: int,
    avg_pages: int,
    multimodal_ratio: float = 0.3
) -> dict:
    """
    Estimate storage and memory requirements.
    
    Args:
        num_documents: Number of documents to process
        avg_pages: Average pages per document
        multimodal_ratio: Fraction of pages with images/tables
    
    Returns:
        dict: Estimated requirements
    """
    # Approximate calculations
    text_per_page = 500  # tokens
    embedding_size = 3072  # dimensions (text-embedding-3-large)
    
    total_tokens = num_documents * avg_pages * text_per_page
    vector_storage = total_tokens * embedding_size * 4 / 1e9  # GB (float32)
    graph_storage = total_tokens * 0.1 / 1e9  # GB (estimated)
    image_storage = num_documents * avg_pages * multimodal_ratio * 0.5 / 1e9  # GB
    
    return {
        "vector_db_storage_gb": vector_storage,
        "graph_storage_gb": graph_storage,
        "image_storage_gb": image_storage,
        "total_storage_gb": vector_storage + graph_storage + image_storage,
        "recommended_ram_gb": max(8, int(total_tokens / 1000000) * 4),
    }
```

---

## 8. Integration with Existing RAG Systems

### 8.1 LightRAG Foundation

RAG-Anything is built on top of LightRAG, inheriting all its capabilities:

```python
# LightRAG features inherited
lightrag_features = [
    "Dual-level retrieval (entity + chunk)",
    "Knowledge graph construction",
    "Multiple storage backends (JSON, KV, Vector DB)",
    "Streaming responses",
    "Caching (LLM responses, embeddings)",
    "Batch processing",
]
```

### 8.2 Migration from Text-Only RAG

```python
# Before: Text-only LightRAG
from lightrag import LightRAG

rag = LightRAG(
    working_dir="./storage",
    llm_model_func=llm_func,
    embedding_func=embed_func,
)

# After: Multimodal RAG-Anything
from raganything import RAGAnything, RAGAnythingConfig

config = RAGAnythingConfig(
    working_dir="./storage",
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=True,
)

rag = RAGAnything(
    config=config,
    llm_model_func=llm_func,
    vision_model_func=vision_func,  # NEW: Vision model
    embedding_func=embed_func,
)
```

### 8.3 Storage Backend Compatibility

| Storage Type | LightRAG | RAG-Anything | Notes |
|--------------|----------|--------------|-------|
| JSON files | ✅ | ✅ | Default, simple |
| KV Storage | ✅ | ✅ | Parse cache integration |
| Vector DB | ✅ | ✅ | Qdrant, Chroma, etc. |
| Graph DB | ✅ | ✅ | Neo4j, NetworkX |

---

## 9. Performance Characteristics and Benchmarks

### 9.1 Benchmark Results

#### DocBench Dataset (229 documents, 1,102 questions)

```
┌─────────────────────────────────────────────────────────────────┐
│ DocBench Performance by Domain                                   │
├────────────────────┬────────────┬────────────┬──────────────────┤
│ Domain             │ RAG-Anything│ MMGraphRAG │ Improvement      │
├────────────────────┼────────────┼────────────┼──────────────────┤
│ Academia (49 docs) │ 64.2%      │ 62.1%      │ +2.1%            │
│ Finance (40 docs)  │ 67.8%      │ 59.4%      │ +8.4%            │
│ Government (44)    │ 58.9%      │ 55.6%      │ +3.3%            │
│ Legal (46 docs)    │ 61.3%      │ 58.2%      │ +3.1%            │
│ News (50 docs)     │ 65.7%      │ 64.8%      │ +0.9%            │
├────────────────────┼────────────┼────────────┼──────────────────┤
│ Overall            │ 63.4%      │ 61.0%      │ +2.4%            │
└────────────────────┴────────────┴────────────┴──────────────────┘
```

#### Document Length Impact

```
┌─────────────────────────────────────────────────────────────────┐
│ Performance vs Document Length (DocBench)                        │
├────────────────────┬────────────┬────────────┬──────────────────┤
│ Page Range         │ RAG-Anything│ MMGraphRAG │ Gap              │
├────────────────────┼────────────┼────────────┼──────────────────┤
│ 0-50 pages         │ 61.5%      │ 60.2%      │ +1.3%            │
│ 51-100 pages       │ 64.3%      │ 59.8%      │ +4.5%            │
│ 101-200 pages      │ 68.2%      │ 54.6%      │ +13.6%           │
│ 200+ pages         │ 68.8%      │ 55.0%      │ +13.8%           │
└────────────────────┴────────────┴────────────┴──────────────────┘
```

### 9.2 Ablation Study Results

| Configuration | DocBench Accuracy | Impact |
|---------------|-------------------|--------|
| Full RAG-Anything | **63.4%** | Baseline |
| Without reranker | 62.4% | -1.0% |
| Chunk-only (no graph) | 60.0% | -3.4% |
| Text-only | 58.4% | -5.0% |

### 9.3 Processing Speed Benchmarks

```python
# Approximate processing times (may vary by hardware)
processing_benchmarks = {
    "pdf_10_pages": {
        "cpu": "~30 seconds",
        "gpu": "~10 seconds",
    },
    "pdf_100_pages": {
        "cpu": "~5 minutes",
        "gpu": "~2 minutes",
    },
    "pdf_500_pages": {
        "cpu": "~25 minutes",
        "gpu": "~8 minutes",
    },
    "query_latency": {
        "local": "~1-2 seconds",
        "hybrid": "~3-5 seconds",
        "vlm_enhanced": "~5-10 seconds",
    },
}
```

---

## 10. API Reference

### 10.1 Core RAGAnything Class

```python
class RAGAnything:
    """
    Multimodal Document Processing Pipeline
    
    Combines document parsing with multimodal RAG capabilities.
    """
    
    def __init__(
        self,
        config: RAGAnythingConfig = None,
        lightrag: LightRAG = None,          # Pre-initialized LightRAG
        llm_model_func: Callable = None,    # LLM function
        vision_model_func: Callable = None, # Vision model function
        embedding_func: Callable = None,    # Embedding function
        lightrag_kwargs: Dict = None,       # Additional LightRAG config
    ):
        """
        Initialize RAG-Anything.
        
        Either provide a pre-initialized LightRAG instance, or
        provide llm_model_func and embedding_func for automatic setup.
        """
        pass
    
    # Document Processing Methods
    # ---------------------------
    
    async def process_document_complete(
        self,
        file_path: str,
        output_dir: str = None,
        parse_method: str = "auto",
    ) -> Dict[str, Any]:
        """
        Complete document processing: parse + insert into knowledge graph.
        
        Args:
            file_path: Path to document (PDF, image, Office, etc.)
            output_dir: Output directory for parsed content
            parse_method: "auto", "ocr", or "txt"
        
        Returns:
            Processing results with statistics
        """
        pass
    
    async def insert_content_list(
        self,
        content_list: List[Dict],
        file_path: str,
        doc_id: str = None,
    ) -> Dict[str, Any]:
        """
        Insert pre-parsed content directly into knowledge graph.
        
        Args:
            content_list: List of content items (text, image, table, equation)
            file_path: Original document path for reference
            doc_id: Optional document ID
        
        Returns:
            Insertion results
        """
        pass
    
    # Query Methods
    # -------------
    
    async def aquery(
        self,
        query: str,
        mode: str = "mix",
        system_prompt: str = None,
        vlm_enhanced: bool = None,
        **kwargs
    ) -> str:
        """
        Pure text query (with optional VLM enhancement).
        
        Args:
            query: Query text
            mode: Query mode ("local", "global", "hybrid", "naive", "mix", "bypass")
            system_prompt: Optional system prompt
            vlm_enhanced: Auto-process images in retrieved context
        
        Returns:
            Query result
        """
        pass
    
    async def aquery_with_multimodal(
        self,
        query: str,
        multimodal_content: List[Dict] = None,
        mode: str = "mix",
        **kwargs
    ) -> str:
        """
        Multimodal query with images/tables/equations.
        
        Args:
            query: Base query text
            multimodal_content: List of multimodal items
                - {"type": "image", "img_path": "...", "image_caption": [...]}
                - {"type": "table", "table_data": "...", "table_caption": "..."}
                - {"type": "equation", "latex": "...", "equation_caption": "..."}
        
        Returns:
            Query result
        """
        pass
    
    async def aquery_vlm_enhanced(
        self,
        query: str,
        mode: str = "mix",
        system_prompt: str = None,
        extra_safe_dirs: List[str] = None,
        **kwargs
    ) -> str:
        """
        VLM-enhanced query for image-heavy documents.
        
        Automatically:
        1. Retrieves relevant context
        2. Extracts image paths
        3. Encodes images to base64
        4. Sends to VLM for multimodal analysis
        
        Args:
            query: Query text
            mode: Underlying query mode
            extra_safe_dirs: Additional directories for image access
        
        Returns:
            VLM analysis result
        """
        pass
    
    # Synchronous Wrappers
    # --------------------
    
    def query(self, query: str, mode: str = "mix", **kwargs) -> str:
        """Synchronous version of aquery."""
        pass
    
    def query_with_multimodal(
        self,
        query: str,
        multimodal_content: List[Dict] = None,
        mode: str = "mix",
        **kwargs
    ) -> str:
        """Synchronous version of aquery_with_multimodal."""
        pass
    
    # Utility Methods
    # ---------------
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information."""
        pass
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get processor information and status."""
        pass
    
    def check_parser_installation(self) -> bool:
        """Check if configured parser is properly installed."""
        pass
    
    async def finalize_storages(self):
        """Cleanup and persist all storage."""
        pass
```

### 10.2 Configuration Class

```python
@dataclass
class RAGAnythingConfig:
    """Configuration for RAG-Anything with environment variable support."""
    
    # Directory Configuration
    working_dir: str = "./rag_storage"
    parser_output_dir: str = "./output"
    
    # Parser Configuration
    parse_method: str = "auto"      # "auto", "ocr", "txt"
    parser: str = "mineru"          # "mineru" or "docling"
    display_content_stats: bool = True
    
    # Multimodal Processing
    enable_image_processing: bool = True
    enable_table_processing: bool = True
    enable_equation_processing: bool = True
    
    # Batch Processing
    max_concurrent_files: int = 1
    supported_file_extensions: List[str] = [
        ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff",
        ".tif", ".gif", ".webp", ".doc", ".docx",
        ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".md"
    ]
    recursive_folder_processing: bool = True
    
    # Context Extraction
    context_window: int = 1
    context_mode: str = "page"
    max_context_tokens: int = 2000
    include_headers: bool = True
    include_captions: bool = True
    context_filter_content_types: List[str] = ["text"]
    
    # Path Handling
    use_full_path: bool = False
```

---

## 11. Integration Strategy for Agent Zero

### 11.1 Architecture Integration

```python
# Proposed integration with Agent Zero document_query tool

┌─────────────────────────────────────────────────────────────────────────────┐
│                     Agent Zero Multimodal RAG Integration                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐         ┌────────────────────────────────────────────┐  │
│  │  document_query │────────▶│           RAG-Anything Backend             │  │
│  │     Tool        │         │                                            │  │
│  └────────────────┘         │  ┌──────────────┐  ┌──────────────────────┐ │  │
│                              │  │   Document   │  │   Multimodal Query   │ │  │
│  Input:                      │  │   Parser     │  │       Engine         │ │  │
│  - URL/path to document      │  │  (MinerU)    │  │                      │ │  │
│  - Query text                │  └──────────────┘  └──────────────────────┘ │  │
│  - Optional: multimodal      │         │                     │           │  │
│    content                   │         ▼                     ▼           │  │
│                              │  ┌──────────────┐  ┌──────────────────────┐ │  │
│  Output:                     │  │   Knowledge  │◀─│    Retrieval +       │ │  │
│  - Text content              │  │    Graph     │  │    VLM Processing    │ │  │
│  - Query answers             │  └──────────────┘  └──────────────────────┘ │  │
│  - Multimodal analysis       │                                            │  │
│                              └────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Implementation Approach

#### Phase 1: Core Integration

```python
# 1. Add RAG-Anything as a dependency
# requirements.txt or pyproject.toml
dependencies = [
    "raganything[all]>=0.1.0",
    "mineru[core]",
]

# 2. Create RAG-Anything wrapper class
# File: /a0/python/helpers/multimodal_rag.py

class MultimodalRAG:
    """
    Wrapper for RAG-Anything integration with Agent Zero.
    Manages singleton instance and provides simplified interface.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, config: RAGAnythingConfig = None) -> "MultimodalRAG":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def __init__(self, config: RAGAnythingConfig = None):
        self.config = config or RAGAnythingConfig(
            working_dir="/a0/usr/workdir/rag_storage",
            parser_output_dir="/a0/usr/workdir/parsed_output",
        )
        self.rag = None
        self._initialized = False
    
    async def initialize(
        self,
        llm_model_func: Callable,
        vision_model_func: Callable,
        embedding_func: Callable,
    ):
        """Initialize RAG-Anything with model functions."""
        if self._initialized:
            return
        
        self.rag = RAGAnything(
            config=self.config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embedding_func,
        )
        
        # Ensure initialization
        await self.rag._ensure_lightrag_initialized()
        self._initialized = True
    
    async def process_document(self, file_path: str) -> Dict:
        """Process a document into the knowledge graph."""
        return await self.rag.process_document_complete(file_path)
    
    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        multimodal_content: List[Dict] = None,
        vlm_enhanced: bool = False,
    ) -> str:
        """Execute a query against processed documents."""
        if multimodal_content:
            return await self.rag.aquery_with_multimodal(
                query, multimodal_content, mode=mode
            )
        return await self.rag.aquery(query, mode=mode, vlm_enhanced=vlm_enhanced)
```

#### Phase 2: Tool Integration

```python
# File: /a0/python/tools/document_query.py (enhanced)

from python.helpers.multimodal_rag import MultimodalRAG

def document_query(
    document: str | List[str],
    queries: List[str] = None,
    multimodal_mode: str = "auto",  # "auto", "text", "vlm"
    **kwargs
) -> str:
    """
    Enhanced document_query with multimodal support.
    
    Args:
        document: URL or path to document(s)
        queries: List of questions to answer
        multimodal_mode: 
            - "auto": Auto-detect multimodal content
            - "text": Text-only processing
            - "vlm": Force VLM-enhanced processing
    """
    # Detect if multimodal processing is needed
    is_multimodal = detect_multimodal_content(document)
    
    if is_multimodal and multimodal_mode != "text":
        # Use RAG-Anything for multimodal documents
        rag = MultimodalRAG.get_instance()
        
        # Process document
        await rag.process_document(document)
        
        # Execute queries
        results = []
        for query in (queries or []):
            result = await rag.query(
                query,
                mode="hybrid",
                vlm_enhanced=(multimodal_mode == "vlm")
            )
            results.append(result)
        
        return format_results(results)
    else:
        # Use existing text-only processing
        return existing_text_processing(document, queries)
```

### 11.3 Configuration Integration

```python
# Environment variables for Agent Zero integration

# .env additions
RAG_ANYTHING_WORKING_DIR=/a0/usr/workdir/rag_storage
RAG_ANYTHING_PARSER=mineru
RAG_ANYTHING_PARSE_METHOD=auto
RAG_ANYTHING_ENABLE_IMAGE=true
RAG_ANYTHING_ENABLE_TABLE=true
RAG_ANYTHING_ENABLE_EQUATION=true
RAG_ANYTHING_DEVICE=cuda  # or "cpu"
RAG_ANYTHING_MAX_CONCURRENT_FILES=1
RAG_ANYTHING_CONTEXT_WINDOW=1
RAG_ANYTHING_MAX_CONTEXT_TOKENS=2000
```

### 11.4 Model Function Integration

```python
# Integrate with Agent Zero's existing LLM infrastructure

def create_llm_model_func(agent) -> Callable:
    """Create LLM function from Agent Zero's configuration."""
    
    async def llm_model_func(
        prompt: str,
        system_prompt: str = None,
        history_messages: List[Dict] = None,
        **kwargs
    ) -> str:
        # Use Agent Zero's LLM infrastructure
        response = await agent.call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            history=history_messages,
            **kwargs
        )
        return response
    
    return llm_model_func


def create_vision_model_func(agent) -> Callable:
    """Create vision function from Agent Zero's configuration."""
    
    async def vision_model_func(
        prompt: str,
        system_prompt: str = None,
        image_data: str = None,
        messages: List[Dict] = None,
        **kwargs
    ) -> str:
        # Use Agent Zero's multimodal LLM (if available)
        if messages:
            # Multimodal messages format
            response = await agent.call_multimodal_llm(
                messages=messages,
                **kwargs
            )
        elif image_data:
            # Single image format
            response = await agent.call_vision_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                image_base64=image_data,
                **kwargs
            )
        else:
            # Fallback to text
            response = await agent.call_llm(prompt, system_prompt)
        
        return response
    
    return vision_model_func


def create_embedding_func(agent) -> Callable:
    """Create embedding function from Agent Zero's configuration."""
    
    from lightrag.utils import EmbeddingFunc
    
    async def embed_func(texts: List[str]) -> List[List[float]]:
        # Use Agent Zero's embedding infrastructure
        embeddings = await agent.get_embeddings(texts)
        return embeddings
    
    return EmbeddingFunc(
        embedding_dim=agent.config.embedding_dim,
        max_token_size=8192,
        func=embed_func
    )
```

### 11.5 Usage Examples

```python
# Example 1: Process a research paper with figures

result = await document_query(
    document="https://arxiv.org/pdf/2401.00001.pdf",
    queries=[
        "What is the main contribution?",
        "Explain the architecture diagram in Figure 3",
        "Compare the results in Table 2 with related work"
    ],
    multimodal_mode="vlm"  # Enable VLM for figure analysis
)

# Example 2: Process financial report with tables

result = await document_query(
    document="/path/to/annual_report.pdf",
    queries=[
        "What were the Q4 revenue figures?",
        "Analyze the trends shown in the financial tables"
    ],
    multimodal_mode="auto"
)

# Example 3: Multimodal query with external data

result = await document_query(
    document="/path/to/specification.pdf",
    queries=[
        "Compare this table with the specification requirements"
    ],
    multimodal_content=[{
        "type": "table",
        "table_data": """Requirement,Value
        Max Latency,100ms
        Throughput,1000 req/s
        """,
        "table_caption": "Performance Requirements"
    }]
)
```

---

## 12. Comparison with Traditional Text-Only RAG

### 12.1 Feature Comparison

| Feature | Traditional RAG | RAG-Anything |
|---------|----------------|--------------|
| Text processing | ✅ | ✅ |
| Image understanding | ❌ | ✅ VLM integration |
| Table extraction | ❌ (text only) | ✅ Structured extraction |
| Equation handling | ❌ (text only) | ✅ LaTeX parsing |
| Cross-modal retrieval | ❌ | ✅ Dual-graph approach |
| Document structure | ❌ Lost | ✅ Preserved |
| Long document handling | Degraded | Optimized |
| Knowledge graph | Optional | Built-in |

### 12.2 Performance Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│ Performance: Traditional RAG vs RAG-Anything                     │
├────────────────────┬────────────────┬───────────────────────────┤
│ Document Type       │ Text-Only RAG  │ RAG-Anything              │
├────────────────────┼────────────────┼───────────────────────────┤
│ Pure text          │ 100% (baseline)│ ~100% (equivalent)        │
│ Text + images      │ 60-70%         │ 85-95% (+25-35%)          │
│ Text + tables      │ 70-80%         │ 90-95% (+15%)             │
│ Text + equations   │ 50-60%         │ 85-90% (+30%)             │
│ Mixed multimodal   │ 40-60%         │ 80-90% (+30-40%)          │
│ Long (>100 pages)  │ 50-60%         │ 70-80% (+20%)             │
└────────────────────┴────────────────┴───────────────────────────┘
```

### 12.3 Resource Comparison

| Resource | Traditional RAG | RAG-Anything | Notes |
|----------|----------------|--------------|-------|
| CPU | Low | Medium | More processing for multimodal |
| RAM | 4-8 GB | 8-16 GB | Graph storage overhead |
| GPU | Optional | Recommended | For MinerU + VLM |
| Storage | Document size | 2-3x doc size | Graph + vectors |
| API costs | Text tokens | Text + Vision | Higher for multimodal |

---

## 13. Implementation Recommendations

### 13.1 Recommended Configuration

```python
# Production-ready configuration
recommended_config = RAGAnythingConfig(
    # Storage
    working_dir="/a0/usr/workdir/rag_storage",
    parser_output_dir="/a0/usr/workdir/parsed_output",
    
    # Parser
    parser="mineru",
    parse_method="auto",
    
    # Enable all multimodal features
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=True,
    
    # Context for better understanding
    context_window=1,
    context_mode="page",
    max_context_tokens=2000,
    include_headers=True,
    include_captions=True,
    
    # Batch processing
    max_concurrent_files=1,  # Increase for batch jobs
    recursive_folder_processing=True,
)

# LightRAG parameters for better retrieval
recommended_lightrag_kwargs = {
    "top_k": 60,
    "chunk_top_k": 5,
    "max_entity_tokens": 20000,
    "max_relation_tokens": 20000,
    "max_total_tokens": 32000,
    "chunk_token_size": 1200,
    "chunk_overlap_token_size": 100,
    "enable_llm_cache": True,
}
```

### 13.2 Installation Steps

```bash
# 1. Install RAG-Anything with all dependencies
pip install raganything[all]

# 2. Install MinerU with GPU support (if available)
pip install mineru[core]

# 3. Install LibreOffice for Office document support
# Ubuntu/Debian:
sudo apt-get install libreoffice

# 4. Verify installation
python -c "from raganything import RAGAnything; print('OK')"
```

### 13.3 Deployment Considerations

#### For CPU-Only Environments

```python
config = RAGAnythingConfig(
    parser="docling",  # Docling may be faster on CPU
    parse_method="txt",  # Skip OCR if not needed
)
```

#### For GPU Environments

```python
config = RAGAnythingConfig(
    parser="mineru",
    parse_method="auto",
)

# Ensure CUDA is available
import torch
assert torch.cuda.is_available()
```

#### For Production Scale

```python
# Use external vector database
lightrag_kwargs = {
    "vector_db_storage_cls": YourVectorDB,  # Qdrant, Chroma, etc.
    "kv_storage": YourKVStorage,             # Redis, etc.
    "enable_llm_cache": True,
}
```

### 13.4 Error Handling and Fallbacks

```python
async def robust_document_query(document: str, query: str) -> str:
    """Robust query with fallbacks."""
    
    try:
        # Try multimodal processing
        rag = MultimodalRAG.get_instance()
        await rag.process_document(document)
        return await rag.query(query, vlm_enhanced=True)
    
    except Exception as e:
        if "GPU" in str(e) or "CUDA" in str(e):
            # Fallback to CPU mode
            logger.warning("GPU not available, falling back to CPU")
            config = RAGAnythingConfig(parser="docling")
            rag = MultimodalRAG.get_instance(config)
            await rag.process_document(document)
            return await rag.query(query)
        
        elif "vision" in str(e).lower():
            # Fallback to text-only
            logger.warning("Vision model not available, text-only mode")
            return await rag.query(query, vlm_enhanced=False)
        
        else:
            # Ultimate fallback to basic document_query
            logger.error(f"RAG-Anything failed: {e}")
            return await basic_text_query(document, query)
```

---

## 14. Conclusion and Next Steps

### 14.1 Summary

RAG-Anything provides Agent Zero with powerful multimodal document understanding capabilities:

✅ **Comprehensive multimodal support** - Images, tables, equations, charts
✅ **Superior performance** - 63.4% accuracy on DocBench (vs 51.2% for GPT-4o-mini)
✅ **Long document optimization** - 13+ point improvement for 100+ page documents
✅ **Flexible integration** - Compatible with existing Agent Zero infrastructure
✅ **Production-ready** - Battle-tested on real-world documents

### 14.2 Recommended Integration Path

1. **Phase 1** (Week 1): Add RAG-Anything dependency and basic wrapper
2. **Phase 2** (Week 2): Integrate with document_query tool
3. **Phase 3** (Week 3): Add multimodal query support
4. **Phase 4** (Week 4): Performance optimization and testing

### 14.3 Key Files to Create

| File | Purpose |
|------|---------|
| `/a0/python/helpers/multimodal_rag.py` | RAG-Anything wrapper class |
| `/a0/python/tools/multimodal_query.py` | Multimodal query tool |
| `/a0/prompts/default/tools/multimodal_query.md` | Tool documentation |
| `/a0/requirements/multimodal.txt` | Additional dependencies |

---

## Appendix A: Quick Start Code

```python
#!/usr/bin/env python
"""
Quick start example for RAG-Anything integration.
"""

import asyncio
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

async def main():
    # 1. Configuration
    config = RAGAnythingConfig(
        working_dir="./rag_storage",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    
    # 2. Model functions
    def llm_func(prompt, system_prompt=None, **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            api_key="your-api-key",
        )
    
    def vision_func(prompt, image_data=None, messages=None, **kwargs):
        if messages:
            return openai_complete_if_cache(
                "gpt-4o", "", messages=messages,
                api_key="your-api-key",
            )
        # ... handle single image
    
    embed_func = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts, model="text-embedding-3-large",
            api_key="your-api-key",
        ),
    )
    
    # 3. Initialize
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        vision_model_func=vision_func,
        embedding_func=embed_func,
    )
    
    # 4. Process document
    await rag.process_document_complete("research_paper.pdf")
    
    # 5. Query
    result = await rag.aquery(
        "Explain the architecture diagram",
        vlm_enhanced=True
    )
    print(result)
    
    # 6. Cleanup
    await rag.finalize_storages()

if __name__ == "__main__":
    asyncio.run(main())
```

---

*Document Version: 1.0*
*Generated: 2026-02-22*
*Repository: https://github.com/HKUDS/RAG-Anything*
*Paper: https://arxiv.org/abs/2510.12323*
