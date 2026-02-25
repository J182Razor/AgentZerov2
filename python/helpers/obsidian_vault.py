"""
Obsidian Vault Manager - Native Agent Zero Integration
Direct file system access to Obsidian vaults with full CRUD operations.
"""
import os
import re
import json
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Union, AsyncIterator
from dataclasses import dataclass, field, asdict
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class NoteMetadata:
    """Extracted metadata from Obsidian note."""
    title: str = ""
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    char_count: int = 0
    links: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)


@dataclass
class Note:
    """Represents an Obsidian note."""
    path: str
    content: str = ""
    metadata: NoteMetadata = field(default_factory=NoteMetadata)
    exists: bool = True
    is_canvas: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "metadata": asdict(self.metadata),
            "exists": self.exists,
            "is_canvas": self.is_canvas
        }


class ObsidianVault:
    """
    Manages direct access to Obsidian vault files.
    Provides async CRUD operations, metadata extraction, and file watching.
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self._cache: Dict[str, Note] = {}
        self._cache_enabled: bool = True
        self._lock = asyncio.Lock()
        self._change_callbacks: List[callable] = []
        self._observer = None
        
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        
        # Check for .obsidian folder
        obsidian_dir = self.vault_path / ".obsidian"
        if not obsidian_dir.exists():
            logger.warning(f"No .obsidian directory found at {vault_path}")
    
    def _resolve_path(self, note_path: str) -> Path:
        """Resolve note path relative to vault root."""
        note_path = note_path.lstrip("/")
        return self.vault_path / note_path
    
    def _parse_frontmatter(self, content: str) -> tuple:
        """Parse YAML frontmatter from note content."""
        frontmatter = {}
        body = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except Exception as e:
                    logger.warning(f"Failed to parse frontmatter: {e}")
        
        return frontmatter, body
    
    def _extract_metadata(self, content: str, path: str) -> NoteMetadata:
        """Extract all metadata from note content."""
        frontmatter, body = self._parse_frontmatter(content)
        
        # Extract tags from content
        inline_tags = re.findall(r"#([\w/-]+)", body)
        frontmatter_tags = frontmatter.get("tags", [])
        if isinstance(frontmatter_tags, str):
            frontmatter_tags = [frontmatter_tags]
        
        # Extract wiki links
        wiki_links = re.findall(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]", body)
        
        # Get file stats
        stat = os.stat(path) if os.path.exists(path) else None
        
        return NoteMetadata(
            title=frontmatter.get("title", Path(path).stem),
            aliases=frontmatter.get("aliases", []),
            tags=list(set(inline_tags + frontmatter_tags)),
            created=datetime.fromtimestamp(stat.st_ctime) if stat else None,
            modified=datetime.fromtimestamp(stat.st_mtime) if stat else None,
            frontmatter=frontmatter,
            word_count=len(body.split()),
            char_count=len(body),
            links=wiki_links,
            backlinks=[]
        )
    
    async def read_note(self, note_path: str, parse_metadata: bool = True) -> Note:
        """Read a note from the vault."""
        full_path = self._resolve_path(note_path)
        
        if not full_path.exists():
            return Note(path=note_path, exists=False)
        
        async with self._lock:
            try:
                async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                
                is_canvas = str(full_path).endswith(".canvas")
                note = Note(path=note_path, content=content, exists=True, is_canvas=is_canvas)
                
                if parse_metadata and not is_canvas:
                    note.metadata = self._extract_metadata(content, str(full_path))
                
                if self._cache_enabled:
                    self._cache[note_path] = note
                
                return note
            except Exception as e:
                logger.error(f"Failed to read note {note_path}: {e}")
                return Note(path=note_path, exists=False)
    
    async def write_note(self, note_path: str, content: str, frontmatter: Optional[Dict] = None, overwrite: bool = False) -> Note:
        """Write a note to the vault."""
        full_path = self._resolve_path(note_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with self._lock:
            try:
                if frontmatter:
                    import yaml
                    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
                    full_content = f"---\n{fm_str}---\n\n{content}"
                else:
                    full_content = content
                
                async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                    await f.write(full_content)
                
                return await self.read_note(note_path)
            except Exception as e:
                logger.error(f"Failed to write note {note_path}: {e}")
                raise
    
    async def delete_note(self, note_path: str) -> bool:
        """Delete a note from the vault."""
        full_path = self._resolve_path(note_path)
        
        async with self._lock:
            try:
                if full_path.exists():
                    full_path.unlink()
                    if note_path in self._cache:
                        del self._cache[note_path]
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete note {note_path}: {e}")
                raise
    
    async def list_notes(self, folder: str = "", recursive: bool = True, include_canvas: bool = True) -> List[str]:
        """List all notes in a folder."""
        folder_path = self._resolve_path(folder)
        
        if not folder_path.exists():
            return []
        
        extensions = [".md"]
        if include_canvas:
            extensions.append(".canvas")
        
        notes = []
        pattern = "**/*" if recursive else "*"
        
        for ext in extensions:
            for file_path in folder_path.glob(f"{pattern}{ext}"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.vault_path)
                    notes.append(str(rel_path))
        
        return sorted(notes)
    
    async def search_content(self, query: str, folder: str = "", case_sensitive: bool = False, 
                            regex: bool = False, max_results: int = 100) -> List[Dict]:
        """Search note contents."""
        notes = await self.list_notes(folder)
        results = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags) if regex else re.compile(re.escape(query), flags)
        
        for note_path in notes[:max_results * 10]:
            note = await self.read_note(note_path, parse_metadata=False)
            if not note.exists:
                continue
            
            for match in pattern.finditer(note.content):
                start = max(0, match.start() - 50)
                end = min(len(note.content), match.end() + 50)
                context = note.content[start:end]
                
                results.append({
                    "path": note_path,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "context": "..." + context.replace("\n", " ") + "..."
                })
            
            if len(results) >= max_results:
                break
        
        return results
    
    async def get_graph(self) -> Dict[str, Any]:
        """Build link graph for the entire vault."""
        notes = await self.list_notes()
        graph = {"nodes": [], "edges": []}
        link_map: Dict[str, List[str]] = {}
        
        for note_path in notes:
            note = await self.read_note(note_path)
            if not note.exists:
                continue
            
            graph["nodes"].append({
                "id": note_path,
                "title": note.metadata.title,
                "tags": note.metadata.tags,
                "links": note.metadata.links
            })
            
            for link in note.metadata.links:
                if note_path not in link_map:
                    link_map[note_path] = []
                link_map[note_path].append(link)
        
        for source, targets in link_map.items():
            for target in targets:
                graph["edges"].append({"source": source, "target": target})
        
        return graph
    
    async def get_tags(self) -> Dict[str, int]:
        """Get all tags and their frequency."""
        notes = await self.list_notes()
        tag_count: Dict[str, int] = {}
        
        for note_path in notes:
            note = await self.read_note(note_path)
            if note.exists:
                for tag in note.metadata.tags:
                    tag_count[tag] = tag_count.get(tag, 0) + 1
        
        return dict(sorted(tag_count.items(), key=lambda x: -x[1]))
    
    def __repr__(self):
        return f"ObsidianVault(path={self.vault_path})"
