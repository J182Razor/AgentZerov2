"""
Obsidian Index Engine - Fast full-text and semantic search for vaults.
"""
import os
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
import logging
import threading

logger = logging.getLogger(__name__)

@dataclass
class IndexEntry:
    """Index entry for a note."""
    path: str
    title: str
    content_hash: str
    word_count: int
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    modified: Optional[datetime] = None
    embedding_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ObsidianIndex:
    """High-performance index for Obsidian vaults using SQLite FTS5."""
    
    def __init__(self, vault_path: str, index_dir: Optional[str] = None):
        self.vault_path = Path(vault_path)
        self.index_dir = Path(index_dir) if index_dir else self.vault_path / ".obsidian" / "a0-index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.index_dir / "index.db"
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with FTS5."""
        with self._lock:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS notes (
                    path TEXT PRIMARY KEY,
                    title TEXT,
                    content_hash TEXT,
                    word_count INTEGER,
                    modified TEXT
                );
                CREATE TABLE IF NOT EXISTS tags (
                    note_path TEXT,
                    tag TEXT,
                    PRIMARY KEY (note_path, tag)
                );
                CREATE TABLE IF NOT EXISTS links (
                    source_path TEXT,
                    target_path TEXT,
                    PRIMARY KEY (source_path, target_path)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    path, title, content,
                    tokenize = 'porter unicode61'
                );
            """)
            self._conn.commit()
    
    async def index_note(self, path: str, content: str, metadata: Dict = None):
        """Index a single note."""
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        title = metadata.get("title", Path(path).stem) if metadata else Path(path).stem
        tags = metadata.get("tags", []) if metadata else []
        links = metadata.get("links", []) if metadata else []
        word_count = len(content.split())
        
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO notes (path, title, content_hash, word_count, modified)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (path, title, content_hash, word_count))
            self._conn.execute("""
                INSERT OR REPLACE INTO notes_fts (path, title, content)
                VALUES (?, ?, ?)
            """, (path, title, content))
            self._conn.execute("DELETE FROM tags WHERE note_path = ?", (path,))
            self._conn.execute("DELETE FROM links WHERE source_path = ?", (path,))
            for tag in tags:
                self._conn.execute("INSERT OR IGNORE INTO tags (note_path, tag) VALUES (?, ?)", (path, tag))
            for link in links:
                self._conn.execute("INSERT OR IGNORE INTO links (source_path, target_path) VALUES (?, ?)", (path, link))
            self._conn.commit()
    
    async def remove_note(self, path: str):
        """Remove a note from the index."""
        with self._lock:
            self._conn.execute("DELETE FROM notes WHERE path = ?", (path,))
            self._conn.execute("DELETE FROM notes_fts WHERE path = ?", (path,))
            self._conn.execute("DELETE FROM tags WHERE note_path = ?", (path,))
            self._conn.execute("DELETE FROM links WHERE source_path = ?", (path,))
            self._conn.commit()
    
    async def search(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Full-text search using FTS5."""
        with self._lock:
            cursor = self._conn.execute("""
                SELECT path, title, snippet(notes_fts, 2, '>>>', '<<<', '...', 30) as snippet, rank
                FROM notes_fts WHERE notes_fts MATCH ?
                ORDER BY rank LIMIT ? OFFSET ?
            """, (query, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    async def search_by_tag(self, tag: str, limit: int = 100) -> List[Dict]:
        """Search notes by tag."""
        with self._lock:
            cursor = self._conn.execute("""
                SELECT n.path, n.title, n.word_count
                FROM notes n JOIN tags t ON n.path = t.note_path
                WHERE t.tag LIKE ? ORDER BY n.modified DESC LIMIT ?
            """, (f"%{tag}%", limit))
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_backlinks(self, path: str) -> List[str]:
        """Get all notes that link to this note."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT source_path FROM links WHERE target_path LIKE ?",
                (f"%{Path(path).stem}%",)
            )
            return [row[0] for row in cursor.fetchall()]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            stats = {}
            for query, key in [
                ("SELECT COUNT(*) FROM notes", "note_count"),
                ("SELECT COUNT(DISTINCT tag) FROM tags", "tag_count"),
                ("SELECT COUNT(*) FROM links", "link_count"),
                ("SELECT SUM(word_count) FROM notes", "total_words")
            ]:
                cursor = self._conn.execute(query)
                stats[key] = cursor.fetchone()[0] or 0
            cursor = self._conn.execute("SELECT tag, COUNT(*) as cnt FROM tags GROUP BY tag ORDER BY cnt DESC LIMIT 20")
            stats["top_tags"] = [(row[0], row[1]) for row in cursor.fetchall()]
            return stats
    
    async def rebuild_index(self, vault):
        """Rebuild the entire index from vault."""
        notes = await vault.list_notes()
        indexed = 0
        for note_path in notes:
            note = await vault.read_note(note_path)
            if note.exists:
                await self.index_note(note_path, note.content, asdict(note.metadata))
                indexed += 1
        return {"indexed": indexed, "total": len(notes)}
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
