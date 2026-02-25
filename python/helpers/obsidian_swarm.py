"""Obsidian Swarm Coordinator - Advanced parallel processing patterns."""
import asyncio
import time
from typing import Dict, List, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class SwarmResult:
    """Result from a swarm operation."""
    success: bool
    data: Any
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0
    pattern_used: str = ""
    agent_count: int = 0


class ObsidianSwarm:
    """Coordinates swarm patterns for Obsidian vault operations."""
    
    def __init__(self, vault, index=None):
        self.vault = vault
        self.index = index
        self._max_concurrency = 20
    
    async def concurrent_read(self, paths: List[str]) -> SwarmResult:
        """Read multiple notes in parallel."""
        start = time.time()
        results = {}
        errors = []
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        async def read_one(path: str):
            async with semaphore:
                try:
                    note = await self.vault.read_note(path)
                    return path, note.to_dict() if note.exists else None
                except Exception as e:
                    return path, f"Error: {str(e)}"
        
        tasks = [read_one(p) for p in paths]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result:
                path, data = result
                if isinstance(data, str) and data.startswith("Error:"):
                    errors.append(data)
                elif data:
                    results[path] = data
        
        return SwarmResult(
            success=len(errors) == 0,
            data=results,
            errors=errors,
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_concurrent",
            agent_count=len(paths)
        )
    
    async def concurrent_write(self, notes: Dict[str, str], frontmatter: Dict = None) -> SwarmResult:
        """Write multiple notes in parallel."""
        start = time.time()
        results = {}
        errors = []
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        async def write_one(path: str, content: str):
            async with semaphore:
                try:
                    note = await self.vault.write_note(path, content, frontmatter=frontmatter)
                    return path, note.to_dict()
                except Exception as e:
                    return path, f"Error: {str(e)}"
        
        tasks = [write_one(p, c) for p, c in notes.items()]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result:
                path, data = result
                if isinstance(data, str) and data.startswith("Error:"):
                    errors.append(data)
                else:
                    results[path] = data
        
        return SwarmResult(
            success=len(errors) == 0,
            data=results,
            errors=errors,
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_concurrent",
            agent_count=len(notes)
        )
    
    async def parallel_search(self, queries: List[str], max_results: int = 50) -> SwarmResult:
        """Execute multiple searches in parallel."""
        start = time.time()
        all_results = {}
        errors = []
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        async def search_one(query: str):
            async with semaphore:
                try:
                    if self.index:
                        results = await self.index.search(query, limit=max_results)
                    else:
                        results = await self.vault.search_content(query, max_results=max_results)
                    return query, results
                except Exception as e:
                    return query, f"Error: {str(e)}"
        
        tasks = [search_one(q) for q in queries]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result:
                query, data = result
                if isinstance(data, str) and data.startswith("Error:"):
                    errors.append(data)
                else:
                    all_results[query] = data
        
        return SwarmResult(
            success=len(errors) == 0,
            data=all_results,
            errors=errors,
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_concurrent",
            agent_count=len(queries)
        )
    
    async def hierarchical_analysis(self, folder: str = "") -> SwarmResult:
        """Hierarchical vault analysis."""
        start = time.time()
        notes = await self.vault.list_notes(folder)
        
        async def analyze_batch(notes_batch: List[str]) -> Dict:
            results = {"notes": [], "total_words": 0, "tags": {}, "links": []}
            for path in notes_batch:
                note = await self.vault.read_note(path)
                if note.exists:
                    results["notes"].append({
                        "path": path,
                        "title": note.metadata.title,
                        "word_count": note.metadata.word_count
                    })
                    results["total_words"] += note.metadata.word_count
                    for tag in note.metadata.tags:
                        results["tags"][tag] = results["tags"].get(tag, 0) + 1
                    results["links"].extend(note.metadata.links)
            return results
        
        batch_size = max(1, len(notes) // self._max_concurrency)
        batches = [notes[i:i+batch_size] for i in range(0, len(notes), batch_size)]
        batch_results = await asyncio.gather(*[analyze_batch(b) for b in batches])
        
        aggregated = {
            "total_notes": len(notes),
            "total_words": sum(r["total_words"] for r in batch_results),
            "all_tags": {},
            "all_links": [],
            "notes_by_word_count": []
        }
        
        for r in batch_results:
            for tag, count in r["tags"].items():
                aggregated["all_tags"][tag] = aggregated["all_tags"].get(tag, 0) + count
            aggregated["all_links"].extend(r["links"])
            aggregated["notes_by_word_count"].extend(r["notes"])
        
        aggregated["notes_by_word_count"].sort(key=lambda x: -x["word_count"])
        aggregated["all_tags"] = dict(sorted(aggregated["all_tags"].items(), key=lambda x: -x[1])[:50])
        
        return SwarmResult(
            success=True,
            data=aggregated,
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_hierarchical",
            agent_count=len(batches) + 1
        )
    
    async def moa_synthesis(self, topic: str, note_paths: List[str]) -> SwarmResult:
        """Mixture of Agents pattern for content synthesis."""
        start = time.time()
        read_result = await self.concurrent_read(note_paths)
        if not read_result.success:
            return SwarmResult(success=False, errors=read_result.errors)
        
        notes_data = read_result.data
        synthesis = {"topic": topic, "notes_analyzed": len(notes_data), "aspects": {}}
        
        for path, note in notes_data.items():
            content = note.get("content", "")
            title = note.get("metadata", {}).get("title", path)
            links = note.get("metadata", {}).get("links", [])
            synthesis["aspects"][title] = {"links": links[:5], "word_count": len(content.split())}
        
        return SwarmResult(
            success=True,
            data=synthesis,
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_moa",
            agent_count=len(note_paths)
        )
    
    async def star_coordinated_search(self, query: str, max_results: int = 50) -> SwarmResult:
        """Star pattern for coordinated search."""
        start = time.time()
        query_variations = [query, query.replace(" ", " OR ")]
        search_result = await self.parallel_search(query_variations, max_results=max_results)
        if not search_result.success:
            return SwarmResult(success=False, errors=search_result.errors)
        
        return SwarmResult(
            success=True,
            data={"query": query, "results": search_result.data},
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_star",
            agent_count=len(query_variations) + 1
        )
    
    async def vote_validation(self, note_paths: List[str]) -> SwarmResult:
        """Voting pattern for note validation."""
        start = time.time()
        read_result = await self.concurrent_read(note_paths)
        if not read_result.success:
            return SwarmResult(success=False, errors=read_result.errors)
        
        validations = {}
        for path, note in read_result.data.items():
            content = note.get("content", "")
            metadata = note.get("metadata", {})
            votes = {
                "has_title": bool(metadata.get("title")),
                "has_tags": len(metadata.get("tags", [])) > 0,
                "has_content": len(content) > 100,
                "word_count_ok": metadata.get("word_count", 0) > 50
            }
            score = sum(1 for v in votes.values() if v) / len(votes)
            validations[path] = {"votes": votes, "score": score, "passed": score >= 0.6}
        
        
        passed_count = sum(1 for v in validations.values() if v["passed"])
        return SwarmResult(
            success=True,
            data={"validations": validations, "summary": {"total": len(note_paths), "passed": passed_count}},
            duration_ms=(time.time() - start) * 1000,
            pattern_used="swarm_vote",
            agent_count=len(note_paths)
        )
