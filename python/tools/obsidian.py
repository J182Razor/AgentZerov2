"""
Obsidian Tool for Agent Zero - Native Vault Integration

Provides async operations for Obsidian vault management with
swarm pattern integration for parallel processing.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from python.helpers.tool import Tool, Response
from python.helpers.obsidian_vault import ObsidianVault, Note

logger = logging.getLogger(__name__)

# Singleton vault instance
_vault_instance: Optional[ObsidianVault] = None
_vault_path: Optional[str] = None


def get_vault_path() -> str:
    """Get vault path from environment or config."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        # Try common locations
        common_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "obsidian",
            Path("/a0/usr/vault"),
        ]
        for p in common_paths:
            if p.exists():
                vault_path = str(p)
                break
    return vault_path


async def get_vault() -> ObsidianVault:
    """Get or create the ObsidianVault singleton."""
    global _vault_instance, _vault_path
    
    current_path = get_vault_path()
    if _vault_instance is None or current_path != _vault_path:
        if not current_path:
            raise ValueError(
                "Obsidian vault path not configured. "
                "Set OBSIDIAN_VAULT_PATH environment variable or ensure vault exists at default location."
            )
        _vault_instance = ObsidianVault(current_path)
        _vault_path = current_path
        logger.info(f"Initialized Obsidian vault at: {current_path}")
    
    return _vault_instance


class obsidian(Tool):
    """
    Native Agent Zero tool for Obsidian vault operations.
    Provides CRUD operations, search, and graph analysis.
    """
    
    async def execute(
        self,
        action: str = "list",
        path: str = "",
        content: str = "",
        frontmatter: str = "",
        folder: str = "",
        query: str = "",
        max_results: int = 100,
        **kwargs
    ) -> Response:
        """
        Execute Obsidian vault operation.
        
        Args:
            action: Operation to perform (read, write, delete, list, search, graph, tags)
            path: Note path relative to vault root
            content: Content for write operations
            frontmatter: YAML frontmatter for write operations (as string)
            folder: Folder path for list operations
            query: Search query for search operations
            max_results: Maximum results for search operations
        """
        try:
            vault = await get_vault()
        except ValueError as e:
            return Response(message=str(e), break_loop=False)
        
        # Route to appropriate method
        action_map = {
            "read": self._read_note,
            "write": self._write_note,
            "delete": self._delete_note,
            "list": self._list_notes,
            "search": self._search_notes,
            "graph": self._get_graph,
            "tags": self._get_tags,
        }
        
        handler = action_map.get(action.lower())
        if not handler:
            return Response(
                message=f"Unknown action: {action}. Valid actions: {', '.join(action_map.keys())}",
                break_loop=False
            )
        
        return await handler(
            vault=vault,
            path=path,
            content=content,
            frontmatter=frontmatter,
            folder=folder,
            query=query,
            max_results=max_results,
            **kwargs
        )
    
    async def _read_note(self, vault: ObsidianVault, path: str, **kwargs) -> Response:
        """Read a note from the vault."""
        if not path:
            return Response(message="Path is required for read operation", break_loop=False)
        
        note = await vault.read_note(path)
        
        if not note.exists:
            return Response(message=f"Note not found: {path}", break_loop=False)
        
        result = note.to_dict()
        response_text = f"# Note: {path}\n\n"
        
        if note.metadata.frontmatter:
            response_text += "## Frontmatter\n```\n"
            for key, value in note.metadata.frontmatter.items():
                response_text += f"{key}: {value}\n"
            response_text += "```\n\n"
        
        response_text += f"## Content\n{note.content}\n\n"
        response_text += "## Metadata\n"
        response_text += f"- Title: {note.metadata.title}\n"
        response_text += f"- Tags: {', '.join(note.metadata.tags) if note.metadata.tags else 'none'}\n"
        response_text += f"- Links: {len(note.metadata.links)}\n"
        response_text += f"- Word Count: {note.metadata.word_count}\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"note": result, "success": True}
        )
    
    async def _write_note(
        self,
        vault: ObsidianVault,
        path: str,
        content: str,
        frontmatter: str = "",
        **kwargs
    ) -> Response:
        """Write a note to the vault."""
        if not path:
            return Response(message="Path is required for write operation", break_loop=False)
        
        if not content:
            return Response(message="Content is required for write operation", break_loop=False)
        
        # Parse frontmatter if provided
        fm_dict = None
        if frontmatter:
            try:
                import yaml
                fm_dict = yaml.safe_load(frontmatter)
            except Exception as e:
                return Response(
                    message=f"Failed to parse frontmatter YAML: {str(e)}",
                    break_loop=False
                )
        
        note = await vault.write_note(path, content, fm_dict)
        
        response_text = f"Note written successfully: {path}\n"
        response_text += f"Word count: {note.metadata.word_count}\n"
        response_text += f"Character count: {note.metadata.char_count}\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"path": path, "success": True, "note": note.to_dict()}
        )
    
    async def _delete_note(self, vault: ObsidianVault, path: str, **kwargs) -> Response:
        """Delete a note from the vault."""
        if not path:
            return Response(message="Path is required for delete operation", break_loop=False)
        
        success = await vault.delete_note(path)
        
        if success:
            return Response(
                message=f"Note deleted successfully: {path}",
                break_loop=False,
                additional={"path": path, "success": True}
            )
        else:
            return Response(
                message=f"Note not found or could not be deleted: {path}",
                break_loop=False,
                additional={"path": path, "success": False}
            )
    
    async def _list_notes(self, vault: ObsidianVault, folder: str = "", **kwargs) -> Response:
        """List notes in a folder."""
        notes = await vault.list_notes(folder)
        
        if not notes:
            return Response(
                message=f"No notes found in folder: {folder or '/'}",
                break_loop=False,
                additional={"notes": [], "count": 0}
            )
        
        response_text = f"# Notes in {folder or '/'}\n\n"
        for i, note_path in enumerate(notes, 1):
            response_text += f"{i}. {note_path}\n"
        
        response_text += f"\nTotal: {len(notes)} notes\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"notes": notes, "count": len(notes)}
        )
    
    async def _search_notes(
        self,
        vault: ObsidianVault,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> Response:
        """Search notes in the vault."""
        if not query:
            return Response(message="Query is required for search operation", break_loop=False)
        
        results = await vault.search_content(query, max_results=max_results)
        
        if not results:
            return Response(
                message=f"No results found for query: {query}",
                break_loop=False,
                additional={"results": [], "count": 0, "query": query}
            )
        
        response_text = f"# Search Results for: {query}\n\n"
        
        for i, result in enumerate(results, 1):
            response_text += f"## {i}. {result['path']}\n"
            response_text += f"Match: `{result['match']}`\n"
            response_text += f"Context: {result['context']}\n\n"
        
        response_text += f"Total: {len(results)} results\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"results": results, "count": len(results), "query": query}
        )
    
    async def _get_graph(self, vault: ObsidianVault, **kwargs) -> Response:
        """Get the link graph for the vault."""
        graph = await vault.get_graph()
        
        response_text = "# Vault Graph\n\n"
        response_text += f"## Nodes ({len(graph['nodes'])} notes)\n"
        
        for node in graph['nodes'][:20]:  # Show first 20
            response_text += f"- {node['title']} ({node['id']})\n"
            if node['tags']:
                response_text += f"  Tags: {', '.join(node['tags'])}\n"
        
        if len(graph['nodes']) > 20:
            response_text += f"... and {len(graph['nodes']) - 20} more\n"
        
        response_text += f"\n## Edges ({len(graph['edges'])} links)\n"
        for edge in graph['edges'][:10]:
            response_text += f"- {edge['source']} -> {edge['target']}\n"
        
        if len(graph['edges']) > 10:
            response_text += f"... and {len(graph['edges']) - 10} more\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"graph": graph, "success": True}
        )
    
    async def _get_tags(self, vault: ObsidianVault, **kwargs) -> Response:
        """Get all tags in the vault."""
        tags = await vault.get_tags()
        
        if not tags:
            return Response(
                message="No tags found in vault",
                break_loop=False,
                additional={"tags": {}, "count": 0}
            )
        
        response_text = "# Vault Tags\n\n"
        for tag, count in list(tags.items())[:50]:
            response_text += f"- #{tag}: {count}\n"
        
        if len(tags) > 50:
            response_text += f"\n... and {len(tags) - 50} more tags\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={"tags": tags, "count": len(tags)}
        )


class obsidian_swarm(Tool):
    """
    Swarm-integrated Obsidian operations.
    Enables parallel processing of vault operations using swarm patterns.
    """
    
    async def execute(
        self,
        action: str = "read",
        paths: str = "",  # Comma-separated paths for parallel read
        query: str = "",
        max_results: int = 100,
        **kwargs
    ) -> Response:
        """
        Execute swarm-based Obsidian operation.
        
        Args:
            action: Operation (read, search)
            paths: Comma-separated list of paths for parallel read
            query: Search query for swarm search
            max_results: Maximum results per search
        """
        try:
            vault = await get_vault()
        except ValueError as e:
            return Response(message=str(e), break_loop=False)
        
        if action == "read":
            return await self._swarm_read(vault, paths)
        elif action == "search":
            return await self._swarm_search(vault, query, max_results)
        else:
            return Response(
                message=f"Unknown swarm action: {action}. Valid: read, search",
                break_loop=False
            )
    
    async def _swarm_read(self, vault: ObsidianVault, paths: str) -> Response:
        """Read multiple notes in parallel."""
        if not paths:
            return Response(message="Paths required for swarm read (comma-separated)", break_loop=False)
        
        path_list = [p.strip() for p in paths.split(",") if p.strip()]
        
        # Parallel read using asyncio.gather
        tasks = [vault.read_note(p) for p in path_list]
        notes = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        errors = []
        
        for path, note in zip(path_list, notes):
            if isinstance(note, Exception):
                errors.append({"path": path, "error": str(note)})
            elif note.exists:
                results[path] = note.to_dict()
            else:
                errors.append({"path": path, "error": "Note not found"})
        
        response_text = "# Swarm Read Results\n\n"
        response_text += f"Read {len(results)} notes successfully\n"
        if errors:
            response_text += f"Errors: {len(errors)}\n\n"
        
        for path, note_data in results.items():
            response_text += f"## {path}\n"
            response_text += f"Words: {note_data['metadata']['word_count']}\n"
            response_text += f"Tags: {', '.join(note_data['metadata']['tags'])}\n\n"
        
        if errors:
            response_text += "## Errors\n"
            for err in errors:
                response_text += f"- {err['path']}: {err['error']}\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors)
            }
        )
    
    async def _swarm_search(self, vault: ObsidianVault, query: str, max_results: int) -> Response:
        """Execute parallel search with multiple query variations."""
        if not query:
            return Response(message="Query required for swarm search", break_loop=False)
        
        # Create query variations for broader search
        queries = [query]
        
        # Add variations: original, lowercase, title case
        if query.lower() != query:
            queries.append(query.lower())
        if query.title() != query:
            queries.append(query.title())
        
        # Parallel search execution
        tasks = [
            vault.search_content(q, max_results=max_results // len(queries))
            for q in queries
        ]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge and deduplicate results
        all_results = {}
        for results in search_results:
            if isinstance(results, Exception):
                continue
            for r in results:
                key = f"{r['path']}:{r['start']}"
                if key not in all_results:
                    all_results[key] = r
        
        # Sort by path
        merged = sorted(all_results.values(), key=lambda x: x['path'])[:max_results]
        
        response_text = "# Swarm Search Results\n\n"
        response_text += f"Query: {query}\n"
        response_text += f"Variations searched: {len(queries)}\n"
        response_text += f"Unique results: {len(merged)}\n\n"
        
        for i, result in enumerate(merged[:20], 1):
            response_text += f"## {i}. {result['path']}\n"
            response_text += f"Match: `{result['match']}`\n"
            response_text += f"Context: {result['context']}\n\n"
        
        if len(merged) > 20:
            response_text += f"... and {len(merged) - 20} more results\n"
        
        return Response(
            message=response_text,
            break_loop=False,
            additional={
                "results": merged,
                "query": query,
                "variations": len(queries),
                "count": len(merged)
            }
        )


class obsidian_config(Tool):
    """Configure Obsidian vault settings."""
    
    async def execute(
        self,
        vault_path: str = "",
        action: str = "status",
        **kwargs
    ) -> Response:
        """
        Configure or check Obsidian vault.
        
        Args:
            vault_path: Set new vault path
            action: status, set, test
        """
        global _vault_instance, _vault_path
        
        if action == "set" and vault_path:
            if not Path(vault_path).exists():
                return Response(
                    message=f"Vault path does not exist: {vault_path}",
                    break_loop=False
                )
            
            # Reset singleton to use new path
            _vault_instance = None
            _vault_path = None
            os.environ["OBSIDIAN_VAULT_PATH"] = vault_path
            
            return Response(
                message=f"Vault path set to: {vault_path}",
                break_loop=False,
                additional={"vault_path": vault_path, "success": True}
            )
        
        elif action == "test":
            try:
                vault = await get_vault()
                notes = await vault.list_notes()
                return Response(
                    message=f"Vault connection successful. Found {len(notes)} notes.",
                    break_loop=False,
                    additional={"success": True, "note_count": len(notes)}
                )
            except Exception as e:
                return Response(
                    message=f"Vault connection failed: {str(e)}",
                    break_loop=False,
                    additional={"success": False, "error": str(e)}
                )
        
        else:  # status
            current_path = get_vault_path()
            status_text = "# Obsidian Configuration\n\n"
            status_text += f"Vault Path: {current_path or 'Not configured'}\n"
            
            if current_path:
                vault_exists = Path(current_path).exists()
                status_text += f"Path Exists: {vault_exists}\n"
                
                if vault_exists:
                    obsidian_dir = Path(current_path) / ".obsidian"
                    status_text += f"Obsidian Config: {'Found' if obsidian_dir.exists() else 'Not found'}\n"
            
            return Response(
                message=status_text,
                break_loop=False,
                additional={
                    "vault_path": current_path,
                    "configured": bool(current_path)
                }
            )
