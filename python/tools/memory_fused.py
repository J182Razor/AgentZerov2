"""Enhanced Memory Tools for Agent Zero with fused memory integration

Provides:
- memory_save_enhanced: Save with compression and intelligent routing
- memory_load_enhanced: Hybrid retrieval with RRF fusion
- memory_consolidate: Lifecycle management (decay/merge/prune)
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from python.helpers.tool import Tool, Response

# Default configuration path
DEFAULT_CONFIG_PATH = "/a0/memory_config.json"

# Facade singleton
_facade = None


async def get_facade(config_path: str = DEFAULT_CONFIG_PATH):
    """Get or create the unified memory facade singleton"""
    global _facade
    if _facade is None:
        from python.lib.fused_memory.facade import FusedMemoryConfig, UnifiedMemoryFacade
        config = FusedMemoryConfig.from_file(config_path)
        if not os.path.exists(config_path):
            config = FusedMemoryConfig(
                memvid_path="/a0/usr/memory/fused/memory.mv2",
                simplemem_path="/a0/usr/memory/fused/memory.lancedb",
                kg_path="/a0/usr/memory/fused/knowledge_graph.json",
                embedding_model="text-embedding-3-small",
                local_embedding_model="all-MiniLM-L6-v2",
                enable_memvid=True,
                enable_simplemem=True,
                enable_kg=False,
                enable_compression=True,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        _facade = UnifiedMemoryFacade(config)
        await _facade.initialize()
    return _facade


class MemorySaveEnhanced(Tool):
    """Enhanced memory save with compression and intelligent routing"""

    async def execute(
        self,
        text: str = "",
        area: str = "main",
        modality: Optional[str] = None,
        persons: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        location: Optional[str] = None,
        topic: Optional[str] = None,
        **kwargs
    ) -> Response:
        if not text:
            return Response(message="No content provided to save", break_loop=False)

        metadata = {
            "area": area,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        if persons:
            metadata["persons"] = persons
        if entities:
            metadata["entities"] = entities
        if location:
            metadata["location"] = location
        if topic:
            metadata["topic"] = topic

        modality_enum = None
        if modality:
            from python.lib.fused_memory.facade import ModalityType
            try:
                modality_enum = ModalityType(modality.lower())
            except ValueError:
                pass

        try:
            facade = await get_facade()
            result = await facade.save(
                content=text,
                metadata=metadata,
                modality=modality_enum
            )

            if result.success:
                response_text = f"Memory saved successfully.\n"
                response_text += f"ID: {result.entry_id}\n"
                response_text += f"Modality: {result.modality.value}\n"
                response_text += f"Compression: {result.compression_ratio:.2f}x\n"
                ents = ", ".join(result.entities_extracted[:5]) if result.entities_extracted else "none"
                response_text += f"Entities: {ents}\n"
                response_text += f"Storage: {result.storage_path}"
                return Response(message=response_text, break_loop=False)
            else:
                return Response(message=f"Failed to save memory: {result.error}", break_loop=False)

        except Exception as e:
            # Fallback to standard memory save on error
            from python.helpers.memory import Memory
            db = await Memory.get(self.agent)
            id = await db.insert_text(text, metadata)
            result = self.agent.read_prompt("fw.memory_saved.md", memory_id=id)
            return Response(message=result, break_loop=False)


class MemoryLoadEnhanced(Tool):
    """Enhanced memory load with hybrid retrieval and RRF fusion"""

    DEFAULT_THRESHOLD = 0.5
    DEFAULT_LIMIT = 10

    async def execute(
        self,
        query: str = "",
        mode: str = "hybrid",
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = DEFAULT_LIMIT,
        filter: str = "",
        entities: Optional[List[str]] = None,
        **kwargs
    ) -> Response:
        if not query:
            return Response(
                message=self.agent.read_prompt("fw.memories_not_found.md", query=""),
                break_loop=False
            )

        try:
            facade = await get_facade()
            result = await facade.find(
                query=query,
                mode=mode,
                k=limit,
                filters=None,
                entities=entities
            )

            filtered_results = [
                r for r in result.results
                if r.score >= threshold
            ][:limit]

            if not filtered_results:
                return Response(
                    message=self.agent.read_prompt("fw.memories_not_found.md", query=query),
                    break_loop=False
                )

            formatted = []
            for r in filtered_results:
                entry_text = f"---\n"
                entry_text += f"ID: {r.id}\n"
                entry_text += f"Score: {r.score:.3f}\n"
                entry_text += f"Source: {r.metadata.get('area', 'main')}\n"
                if r.metadata.get('persons'):
                    entry_text += f"Persons: {', '.join(r.metadata['persons'])}\n"
                if r.metadata.get('entities'):
                    entry_text += f"Entities: {', '.join(r.metadata['entities'])}\n"
                if r.metadata.get('location'):
                    entry_text += f"Location: {r.metadata['location']}\n"
                if r.metadata.get('timestamp'):
                    entry_text += f"Timestamp: {r.metadata['timestamp']}\n"
                entry_text += f"Content: {r.content}\n"
                formatted.append(entry_text)

            stats = f"\n---\nRetrieval: {result.mode} mode, {len(filtered_results)} results, {result.retrieval_time_ms:.1f}ms"
            stats += f"\nSources: {', '.join(f'{k}({v})' for k, v in result.sources.items())}"

            return Response(
                message="\n".join(formatted) + stats,
                break_loop=False
            )

        except Exception as e:
            # Fallback to standard memory load on error
            from python.helpers.memory import Memory
            db = await Memory.get(self.agent)
            docs = await db.search_similarity_threshold(
                query=query, limit=limit, threshold=threshold, filter=filter
            )

            if len(docs) == 0:
                result = self.agent.read_prompt("fw.memories_not_found.md", query=query)
            else:
                from python.helpers.memory import Memory
                result = "\n\n".join(Memory.format_docs_plain(docs))

            return Response(message=result, break_loop=False)


class MemoryConsolidate(Tool):
    """Memory lifecycle management: decay, merge, prune"""

    async def execute(
        self,
        action: str = "all",
        decay_days: Optional[int] = None,
        merge_threshold: Optional[float] = None,
        **kwargs
    ) -> Response:
        try:
            facade = await get_facade()

            if action == "stats":
                health = await facade.health_check()
                stats_text = "Memory System Status:\n"
                stats_text += f"- Initialized: {health['initialized']}\n"
                stats_text += f"- Memvid: {'OK' if health['memvid'] else 'NA'}\n"
                stats_text += f"- SimpleMem: {'OK' if health['simplemem'] else 'NA'}\n"
                stats_text += f"- Knowledge Graph: {'OK' if health['kg'] else 'NA'}\n"
                return Response(message=stats_text, break_loop=False)

            result = await facade.consolidate()

            response_text = "Memory Consolidation Results:\n"
            response_text += f"- Decayed: {result.get('decayed', 0)} memories\n"
            response_text += f"- Merged: {result.get('merged', 0)} memories\n"
            response_text += f"- Pruned: {result.get('pruned', 0)} memories\n"

            if result.get('errors'):
                response_text += f"- Errors: {len(result['errors'])}\n"
                for err in result['errors'][:3]:
                    response_text += f"  - {err}\n"

            response_text += f"\nTimestamp: {result.get('timestamp', 'N/A')}"

            return Response(message=response_text, break_loop=False)

        except Exception as e:
            return Response(message=f"Consolidation failed: {str(e)}", break_loop=False)


class MemoryHealth(Tool):
    """Check health of memory system"""

    async def execute(self, **kwargs) -> Response:
        try:
            facade = await get_facade()
            health = await facade.health_check()

            response_text = "# Memory System Health Check\n\n"
            status = "OK - Healthy" if health['initialized'] else "NA - Not Initialized"
            response_text += f"**Status**: {status}\n\n"
            response_text += "| Backend | Status |\n"
            response_text += "|---------|--------|\n"
            response_text += f"| Memvid | {'OK - Connected' if health['memvid'] else 'NA - Disconnected'} |\n"
            response_text += f"| SimpleMem | {'OK - Connected' if health['simplemem'] else 'NA - Disconnected'} |\n"
            response_text += f"| Knowledge Graph | {'OK - Connected' if health['kg'] else 'NA - Disconnected'} |\n"
            response_text += f"\n*Checked at: {health['timestamp']}*"

            return Response(message=response_text, break_loop=False)

        except Exception as e:
            return Response(message=f"Health check failed: {str(e)}", break_loop=False)
