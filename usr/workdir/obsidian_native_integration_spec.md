# Obsidian Native Integration Specification
## Agent Zero Built-in Feature Implementation

**Version:** 1.0.0  
**Date:** 2026-02-24  
**Status:** Master Specification Document  
**Author:** Agent Zero Architecture Team

---

## Executive Summary

This specification defines the comprehensive integration of Obsidian as a native built-in feature within Agent Zero. The integration leverages Agent Zero's MCP (Model Context Protocol) architecture, A2A (Agent-to-Agent) communication, and the complete suite of swarm orchestration patterns to deliver maximum parallel processing capabilities for knowledge management operations.

### Key Objectives

1. **Native Integration** - Obsidian operates as a first-class citizen in Agent Zero, not as an external plugin
2. **Swarm Optimization** - All seven swarm patterns utilized for optimal parallel processing
3. **MCP Protocol** - Native tool access through standardized Model Context Protocol
4. **Direct Vault Access** - Real-time file system operations on Obsidian vaults
5. **Enterprise Scale** - Support for large vaults (100k+ notes) with sub-second query response

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Native Integration Components](#2-native-integration-components)
3. [Swarm Pattern Integration](#3-swarm-pattern-integration)
4. [Implementation Phases](#4-implementation-phases)
5. [File Structure](#5-file-structure)
6. [Configuration](#6-configuration)
7. [API Reference](#7-api-reference)
8. [Security Considerations](#8-security-considerations)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Guide](#10-deployment-guide)

---

## 1. Architecture Overview

### 1.1 High-Level Integration Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT ZERO CORE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Agent 0    │  │  Scheduler   │  │   Memory     │  │    A2A       │    │
│  │   (Master)   │  │   Tasks      │  │   System     │  │   Protocol   │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         └─────────────────┴─────────────────┴─────────────────┘            │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SWARM ORCHESTRATION LAYER                       │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ Sequential │ │ Concurrent │ │   Graph    │ │   Vote     │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │    MoA     │ │    Star    │ │Hierarchical│ │  Router    │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         TOOL LAYER                                   │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │                    OBSIDIAN TOOL SUITE                        │   │   │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │   │   │
│  │  │  │ Note CRUD  │ │  Search    │ │  Graph     │ │ Metadata   │ │   │   │
│  │  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ │   │   │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │   │   │
│  │  │  │  Templates │ │  Canvas    │ │   Sync     │ │  Export    │ │   │   │
│  │  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       MCP PROTOCOL LAYER                             │   │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │   │
│  │  │   MCP Server         │  │        MCP Client                    │ │   │
│  │  │  (Obsidian Tools)    │  │   (External Tool Access)             │ │   │
│  │  └──────────────────────┘  └──────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VAULT ACCESS LAYER                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ File Watch │ │   Index    │ │   Cache    │ │  Lock Mgr  │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │   OBSIDIAN VAULT    │
                          │   (File System)     │
                          │  ┌──────────────┐  │
                          │  │    Notes     │  │
                          │  │  *.md files  │  │
                          │  ├──────────────┤  │
                          │  │   Canvas     │  │
                          │  │ *.canvas files│ │
                          │  ├──────────────┤  │
                          │  │  .obsidian/  │  │
                          │  │   config     │  │
                          │  └──────────────┘  │
                          └─────────────────────┘
```

### 1.2 Component Breakdown

#### 1.2.1 Core Components

| Component | Location | Purpose | Dependencies |
|-----------|----------|---------|--------------|
| ObsidianTool | `/a0/python/tools/obsidian.py` | Main tool class for Obsidian operations | MCP, Swarm patterns |
| ObsidianMCPServer | `/a0/python/tools/obsidian_mcp_server.py` | MCP server exposing Obsidian tools | MCP protocol |
| VaultManager | `/a0/python/helpers/obsidian_vault.py` | File system operations, indexing, caching | asyncio, watchdog |
| SwarmCoordinator | `/a0/python/helpers/obsidian_swarm.py` | Swarm pattern selection and execution | All swarm tools |
| IndexEngine | `/a0/python/helpers/obsidian_index.py` | Full-text search, graph index | sqlite, lancedb |
| TemplateEngine | `/a0/python/helpers/obsidian_templates.py` | Template processing | Jinja2 |

#### 1.2.2 Supporting Components

| Component | Location | Purpose |
|-----------|----------|---------|
| CacheManager | `/a0/python/helpers/obsidian_cache.py` | LRU cache for vault data |
| LockManager | `/a0/python/helpers/obsidian_lock.py` | Concurrent access control |
| WatcherService | `/a0/python/helpers/obsidian_watcher.py` | Real-time file monitoring |
| ExportEngine | `/a0/python/helpers/obsidian_export.py` | Multi-format export |
| SyncEngine | `/a0/python/helpers/obsidian_sync.py` | Multi-vault synchronization |

### 1.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                                     │
└─────────────────────────────────────────────────────────────────────────┘

User Request
     │
     ▼
┌──────────────┐    Parse Intent    ┌──────────────┐
│   Agent 0    │ ─────────────────▶ │ Intent Parser │
└──────────────┘                    └──────────────┘
     │                                     │
     │                                     ▼
     │                            ┌──────────────┐
     │                            │   Swarm      │
     │                            │  Selector    │
     │                            └──────────────┘
     │                                     │
     │                                     ▼
     │                            ┌──────────────┐
     │                            │  Pattern     │
     │                            │  Execution   │
     │                            └──────────────┘
     │                                     │
     │                    ┌────────────────┼────────────────┐
     │                    ▼                ▼                ▼
     │             ┌──────────┐    ┌──────────┐    ┌──────────┐
     │             │ Agent 1  │    │ Agent 2  │    │ Agent N  │
     │             │ (Vault)  │    │ (Index)  │    │ (Graph)  │
     │             └──────────┘    └──────────┘    └──────────┘
     │                    │                │                │
     │                    └────────────────┼────────────────┘
     │                                     ▼
     │                            ┌──────────────┐
     │                            │  Result      │
     │                            │  Aggregator  │
     │                            └──────────────┘
     │                                     │
     └─────────────────────────────────────┘
                                         │
                                         ▼
                                   ┌──────────────┐
                                   │   Response   │
                                   │    to User   │
                                   └──────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      INTERNAL DATA FLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────┐
                    │           VAULT FILE SYSTEM          │
                    │  ┌─────────┐  ┌─────────┐  ┌──────┐ │
                    │  │ note.md │  │ note2.md│  │ ...  │ │
                    │  └────┬────┘  └────┬────┘  └──────┘ │
                    └───────┼────────────┼────────────────┘
                            │            │
                    ┌───────┴────────────┴───────┐
                    │      WatcherService        │
                    │   (inotify / watchdog)     │
                    └───────┬─────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │  IndexQueue │   │ CacheUpdate │   │ EventStream │
  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
         │                 │                 │
         ▼                 ▼                 ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │ IndexEngine │   │CacheManager │   │  WebSocket  │
  │  (SQLite +  │   │   (LRU)     │   │   Events    │
  │  LanceDB)   │   │             │   │             │
  └─────────────┘   └─────────────┘   └─────────────┘
```

### 1.4 Integration Points

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION POINTS MAP                                │
└─────────────────────────────────────────────────────────────────────────┘

Agent Zero Core
│
├──► MCP Protocol (Primary Integration)
│    ├── obsidian_read_note
│    ├── obsidian_write_note
│    ├── obsidian_search
│    ├── obsidian_graph
│    └── obsidian_metadata
│
├──► A2A Protocol (Agent Communication)
│    ├── Vault Agent ↔ Index Agent
│    ├── Graph Agent ↔ Search Agent
│    └── Coordinator ↔ Worker Agents
│
├──► Tool System (Native Tools)
│    ├── /a0/python/tools/obsidian.py
│    ├── /a0/python/tools/obsidian_mcp_server.py
│    └── /a0/python/tools/obsidian_swarm.py
│
├──► Skills System (Contextual Expertise)
│    └── /a0/usr/skills/obsidian/SKILL.md
│
├──► Prompt System (Agent Instructions)
│    ├── /a0/prompts/default/tools/obsidian.md
│    └── /a0/prompts/default/tools/obsidian_swarm.md
│
└──► Scheduler (Automated Tasks)
     ├── Vault Sync Tasks
     ├── Index Rebuild Tasks
     └── Backup Tasks
```

---

## 2. Native Integration Components

### 2.1 MCP Server for Obsidian

The MCP Server exposes Obsidian functionality through the Model Context Protocol, enabling seamless integration with Agent Zero's tool system and external MCP-compatible clients.

#### 2.1.1 MCP Server Implementation

**File:** `/a0/python/tools/obsidian_mcp_server.py`

```python
"""
Obsidian MCP Server - Native Agent Zero Integration
Exposes Obsidian vault operations through Model Context Protocol
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# MCP Protocol imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    ResourceTemplate,
)

# Agent Zero imports
from python.helpers.obsidian_vault import VaultManager
from python.helpers.obsidian_index import IndexEngine
from python.helpers.obsidian_swarm import SwarmCoordinator
from python.helpers.obsidian_cache import CacheManager
from python.helpers.obsidian_watcher import WatcherService


@dataclass
class ObsidianMCPServer:
    """
    MCP Server implementation for Obsidian vault operations.
    Provides native integration with Agent Zero's tool ecosystem.
    """
    
    vault_path: Path
    server_name: str = "obsidian-native"
    server_version: str = "1.0.0"
    
    # Internal components
    vault_manager: VaultManager = field(default=None, init=False)
    index_engine: IndexEngine = field(default=None, init=False)
    swarm_coordinator: SwarmCoordinator = field(default=None, init=False)
    cache_manager: CacheManager = field(default=None, init=False)
    watcher_service: WatcherService = field(default=None, init=False)
    
    # MCP Server instance
    server: Server = field(default=None, init=False)
    
    def __post_init__(self):
        self.server = Server(self.server_name)
        self._setup_handlers()
    
    async def initialize(self):
        """Initialize all internal components"""
        self.vault_manager = VaultManager(self.vault_path)
        self.index_engine = IndexEngine(self.vault_path)
        self.cache_manager = CacheManager(max_size=10000)
        self.swarm_coordinator = SwarmCoordinator(
            vault_manager=self.vault_manager,
            index_engine=self.index_engine,
            cache_manager=self.cache_manager
        )
        self.watcher_service = WatcherService(
            vault_path=self.vault_path,
            on_change=self._handle_vault_change
        )
        
        # Initialize components
        await self.vault_manager.initialize()
        await self.index_engine.initialize()
        await self.watcher_service.start()
    
    def _setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return self._get_tool_definitions()
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            return await self._handle_tool_call(name, arguments)
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            return await self._list_vault_resources()
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            return await self._read_vault_resource(uri)
        
        @self.server.list_resource_templates()
        async def list_resource_templates() -> List[ResourceTemplate]:
            return self._get_resource_templates()
    
    def _get_tool_definitions(self) -> List[Tool]:
        """Define all Obsidian tools exposed via MCP"""
        return [
            # === Note Operations ===
            Tool(
                name="obsidian_read_note",
                description="Read a note from the Obsidian vault by path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the note from vault root"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include frontmatter metadata in response"
                        },
                        "include_links": {
                            "type": "boolean",
                            "default": True,
                            "description": "Extract and return wikilinks"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_write_note",
                description="Create or update a note in the vault",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "frontmatter": {
                            "type": "object",
                            "description": "YAML frontmatter to prepend"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["create", "overwrite", "append", "prepend"],
                            "default": "create"
                        }
                    },
                    "required": ["path", "content"]
                }
            ),
            Tool(
                name="obsidian_delete_note",
                description="Delete a note from the vault",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "trash": {
                            "type": "boolean",
                            "default": True,
                            "description": "Move to trash instead of permanent delete"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_move_note",
                description="Move or rename a note, updating all backlinks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                        "update_links": {
                            "type": "boolean",
                            "default": True,
                            "description": "Update all wikilinks pointing to this note"
                        }
                    },
                    "required": ["source", "destination"]
                }
            ),
            
            # === Search Operations ===
            Tool(
                name="obsidian_search",
                description="Full-text search across vault with advanced filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": ["fulltext", "fuzzy", "regex", "semantic"],
                            "default": "fulltext"
                        },
                        "path_filter": {
                            "type": "string",
                            "description": "Glob pattern to filter paths"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags"
                        },
                        "date_range": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "string"},
                                "end": {"type": "string"}
                            }
                        },
                        "limit": {"type": "integer", "default": 50},
                        "offset": {"type": "integer", "default": 0}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="obsidian_search_by_tag",
                description="Find all notes with specific tags",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "match": {
                            "type": "string",
                            "enum": ["any", "all", "none"],
                            "default": "any"
                        }
                    },
                    "required": ["tags"]
                }
            ),
            Tool(
                name="obsidian_search_by_metadata",
                description="Search notes by frontmatter metadata fields",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {
                            "type": "string",
                            "enum": ["eq", "ne", "gt", "lt", "gte", "lte", "contains", "regex"]
                        },
                        "value": {},
                        "combine": {
                            "type": "string",
                            "enum": ["and", "or"],
                            "default": "and"
                        }
                    },
                    "required": ["field", "operator", "value"]
                }
            ),
            
            # === Graph Operations ===
            Tool(
                name="obsidian_graph",
                description="Get the link graph for the vault or specific notes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Center node for subgraph (optional)"
                        },
                        "depth": {
                            "type": "integer",
                            "default": 2,
                            "description": "Depth of connections to include"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["both", "outgoing", "incoming"],
                            "default": "both"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["edges", "adjacency", "cytoscape"],
                            "default": "edges"
                        }
                    }
                }
            ),
            Tool(
                name="obsidian_backlinks",
                description="Get all notes linking to a specific note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "include_context": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include surrounding context of link"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_forward_links",
                description="Get all links from a specific note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "resolve": {
                            "type": "boolean",
                            "default": True,
                            "description": "Resolve links to actual note paths"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_orphans",
                description="Find orphan notes with no incoming or outgoing links",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "exclude_folders": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            ),
            
            # === Metadata Operations ===
            Tool(
                name="obsidian_get_metadata",
                description="Extract and parse frontmatter metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_set_metadata",
                description="Update frontmatter metadata fields",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "metadata": {"type": "object"},
                        "mode": {
                            "type": "string",
                            "enum": ["merge", "replace"],
                            "default": "merge"
                        }
                    },
                    "required": ["path", "metadata"]
                }
            ),
            Tool(
                name="obsidian_tags",
                description="List all tags used in the vault with counts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sort_by": {
                            "type": "string",
                            "enum": ["name", "count"],
                            "default": "count"
                        },
                        "order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc"
                        }
                    }
                }
            ),
            
            # === Template Operations ===
            Tool(
                name="obsidian_apply_template",
                description="Apply a template to create or update a note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template": {
                            "type": "string",
                            "description": "Template name or path"
                        },
                        "destination": {"type": "string"},
                        "variables": {
                            "type": "object",
                            "description": "Variables to substitute in template"
                        }
                    },
                    "required": ["template", "destination"]
                }
            ),
            Tool(
                name="obsidian_daily_note",
                description="Create or open today's daily note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (default: today)"
                        },
                        "template": {
                            "type": "string",
                            "description": "Template for daily note"
                        },
                        "open": {
                            "type": "boolean",
                            "default": True,
                            "description": "Return content if exists"
                        }
                    }
                }
            ),
            
            # === Canvas Operations ===
            Tool(
                name="obsidian_read_canvas",
                description="Read an Obsidian canvas file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="obsidian_create_canvas",
                description="Create a new canvas with nodes and edges",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "nodes": {
                            "type": "array",
                            "description": "Canvas nodes (text, file, link)"
                        },
                        "edges": {
                            "type": "array",
                            "description": "Connections between nodes"
                        }
                    },
                    "required": ["path"]
                }
            ),
            
            # === Vault Operations ===
            Tool(
                name="obsidian_list_notes",
                description="List all notes in the vault or a folder",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "default": "",
                            "description": "Folder path (empty for root)"
                        },
                        "recursive": {
                            "type": "boolean",
                            "default": True
                        },
                        "extension": {
                            "type": "string",
                            "default": ".md"
                        }
                    }
                }
            ),
            Tool(
                name="obsidian_vault_info",
                description="Get vault statistics and configuration",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="obsidian_reindex",
                description="Rebuild the vault index",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "full": {
                            "type": "boolean",
                            "default": False,
                            "description": "Full reindex (slower but thorough)"
                        }
                    }
                }
            ),
            
            # === Swarm Operations ===
            Tool(
                name="obsidian_swarm_search",
                description="Parallel search across vault using swarm patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "pattern": {
                            "type": "string",
                            "enum": ["concurrent", "hierarchical", "moa", "star"],
                            "default": "concurrent"
                        },
                        "max_agents": {
                            "type": "integer",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="obsidian_swarm_analyze",
                description="Multi-agent analysis of vault content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Analysis task description"
                        },
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Notes to analyze"
                        },
                        "pattern": {
                            "type": "string",
                            "enum": ["moa", "vote", "hierarchical"],
                            "default": "moa"
                        }
                    },
                    "required": ["task"]
                }
            ),
            Tool(
                name="obsidian_swarm_graph",
                description="Parallel graph analysis using swarm patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["clusters", "central_nodes", "paths", "summary"]
                        },
                        "pattern": {
                            "type": "string",
                            "enum": ["star", "hierarchical", "concurrent"],
                            "default": "star"
                        }
                    },
                    "required": ["operation"]
                }
            )
        ]
    
    async def _handle_tool_call(
        self, 
        name: str, 
        arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Route tool calls to appropriate handlers"""
        
        handlers = {
            # Note operations
            "obsidian_read_note": self._handle_read_note,
            "obsidian_write_note": self._handle_write_note,
            "obsidian_delete_note": self._handle_delete_note,
            "obsidian_move_note": self._handle_move_note,
            
            # Search operations
            "obsidian_search": self._handle_search,
            "obsidian_search_by_tag": self._handle_search_by_tag,
            "obsidian_search_by_metadata": self._handle_search_by_metadata,
            
            # Graph operations
            "obsidian_graph": self._handle_graph,
            "obsidian_backlinks": self._handle_backlinks,
            "obsidian_forward_links": self._handle_forward_links,
            "obsidian_orphans": self._handle_orphans,
            
            # Metadata operations
            "obsidian_get_metadata": self._handle_get_metadata,
            "obsidian_set_metadata": self._handle_set_metadata,
            "obsidian_tags": self._handle_tags,
            
            # Template operations
            "obsidian_apply_template": self._handle_apply_template,
            "obsidian_daily_note": self._handle_daily_note,
            
            # Canvas operations
            "obsidian_read_canvas": self._handle_read_canvas,
            "obsidian_create_canvas": self._handle_create_canvas,
            
            # Vault operations
            "obsidian_list_notes": self._handle_list_notes,
            "obsidian_vault_info": self._handle_vault_info,
            "obsidian_reindex": self._handle_reindex,
            
            # Swarm operations
            "obsidian_swarm_search": self._handle_swarm_search,
            "obsidian_swarm_analyze": self._handle_swarm_analyze,
            "obsidian_swarm_graph": self._handle_swarm_graph
        }
        
        handler = handlers.get(name)
        if not handler:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        try:
            result = await handler(arguments)
            return [TextContent(
                type="text", 
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        except Exception as e:
            return [TextContent(
                type="text", 
                text=json.dumps({"error": str(e), "tool": name})
            )]
    
    # === Tool Handler Implementations ===
    
    async def _handle_read_note(self, args: Dict) -> Dict:
        """Read a note from the vault"""
        path = args["path"]
        include_metadata = args.get("include_metadata", True)
        include_links = args.get("include_links", True)
        
        note = await self.vault_manager.read_note(path)
        
        result = {
            "path": path,
            "content": note.content,
            "stat": {
                "size": note.size,
                "modified": note.modified.isoformat(),
                "created": note.created.isoformat()
            }
        }
        
        if include_metadata:
            result["metadata"] = note.frontmatter
        
        if include_links:
            result["links"] = note.links
            result["backlinks"] = await self.index_engine.get_backlinks(path)
        
        return result
    
    async def _handle_write_note(self, args: Dict) -> Dict:
        """Write a note to the vault"""
        path = args["path"]
        content = args["content"]
        frontmatter = args.get("frontmatter")
        mode = args.get("mode", "create")
        
        result = await self.vault_manager.write_note(
            path=path,
            content=content,
            frontmatter=frontmatter,
            mode=mode
        )
        
        # Update index
        await self.index_engine.index_note(path)
        
        return {
            "success": True,
            "path": result.path,
            "created": result.created,
            "modified": result.modified
        }
    
    async def _handle_swarm_search(self, args: Dict) -> Dict:
        """Execute parallel search using swarm patterns"""
        query = args["query"]
        pattern = args.get("pattern", "concurrent")
        max_agents = args.get("max_agents", 5)
        
        # Use swarm coordinator for parallel execution
        result = await self.swarm_coordinator.execute_search(
            query=query,
            pattern=pattern,
            max_agents=max_agents
        )
        
        return result
    
    async def _handle_vault_change(self, event):
        """Handle vault file changes"""
        # Invalidate cache
        self.cache_manager.invalidate(event.path)
        
        # Update index
        if event.type in ("created", "modified"):
            await self.index_engine.index_note(event.path)
        elif event.type == "deleted":
            await self.index_engine.remove_note(event.path)
    
    # Additional handler implementations...
    # (Full implementations for all 25+ tools)

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    import os
    vault_path = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "~/obsidian")).expanduser()
    server = ObsidianMCPServer(vault_path=vault_path)
    await server.initialize()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2.2 Tool Definitions for /a0/python/tools/

#### 2.2.1 Main Obsidian Tool

**File:** `/a0/python/tools/obsidian.py`

```python
"""
Obsidian Tool - Native Agent Zero Tool for Vault Operations
Integrates with MCP server and swarm patterns for maximum performance
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json

from python.tools.tool import Tool
from python.helpers.obsidian_vault import VaultManager
from python.helpers.obsidian_index import IndexEngine
from python.helpers.obsidian_swarm import SwarmCoordinator
from python.helpers.obsidian_cache import CacheManager


@dataclass
class ObsidianTool(Tool):
    """
    Native Agent Zero tool for Obsidian vault operations.
    Provides direct access to vault functionality with swarm integration.
    """
    
    name: str = "obsidian"
    description: str = """Obsidian vault operations tool. 
    Provides comprehensive access to notes, search, graph, metadata, and templates.
    Supports both synchronous and swarm-based parallel operations.
    
    Operations:
    - read: Read a note from the vault
    - write: Create or update a note
    - delete: Remove a note
    - search: Full-text search across vault
    - graph: Get link relationships
    - metadata: Access frontmatter
    - template: Apply templates
    - swarm: Execute parallel operations
    """
    
    # Configuration
    vault_path: Optional[str] = None
    enable_swarm: bool = True
    max_cache_size: int = 10000
    
    # Internal state
    _vault_manager: VaultManager = field(default=None, init=False)
    _index_engine: IndexEngine = field(default=None, init=False)
    _swarm_coordinator: SwarmCoordinator = field(default=None, init=False)
    _cache_manager: CacheManager = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize vault components"""
        vault_path = Path(self.vault_path or self._get_vault_path())
        
        self._vault_manager = VaultManager(vault_path)
        self._index_engine = IndexEngine(vault_path)
        self._cache_manager = CacheManager(max_size=self.max_cache_size)
        
        if self.enable_swarm:
            self._swarm_coordinator = SwarmCoordinator(
                vault_manager=self._vault_manager,
                index_engine=self._index_engine,
                cache_manager=self._cache_manager,
                agent=self.agent  # Reference to parent agent for swarm spawning
            )
    
    def _get_vault_path(self) -> str:
        """Get vault path from environment or config"""
        import os
        return os.environ.get("OBSIDIAN_VAULT_PATH", "~/obsidian")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute Obsidian operation"""
        operation = kwargs.get("operation", "read")
        
        # Initialize if needed
        if not self._initialized:
            await self._initialize_async()
            self._initialized = True
        
        # Route to appropriate handler
        handlers = {
            "read": self._handle_read,
            "write": self._handle_write,
            "delete": self._handle_delete,
            "move": self._handle_move,
            "search": self._handle_search,
            "graph": self._handle_graph,
            "metadata": self._handle_metadata,
            "template": self._handle_template,
            "canvas": self._handle_canvas,
            "vault": self._handle_vault,
            "swarm": self._handle_swarm
        }
        
        handler = handlers.get(operation)
        if not handler:
            return {"error": f"Unknown operation: {operation}"}
        
        return await handler(kwargs)
    
    async def _initialize_async(self):
        """Async initialization of components"""
        await self._vault_manager.initialize()
        await self._index_engine.initialize()
    
    async def _handle_read(self, args: Dict) -> Dict:
        """Read note(s) from vault"""
        path = args.get("path")
        
        if path:
            # Single note read
            note = await self._vault_manager.read_note(path)
            return {
                "success": True,
                "note": {
                    "path": note.path,
                    "content": note.content,
                    "metadata": note.frontmatter,
                    "links": note.links
                }
            }
        else:
            # List notes
            folder = args.get("folder", "")
            recursive = args.get("recursive", True)
            notes = await self._vault_manager.list_notes(folder, recursive)
            return {
                "success": True,
                "notes": notes
            }
    
    async def _handle_write(self, args: Dict) -> Dict:
        """Write note to vault"""
        path = args["path"]
        content = args["content"]
        frontmatter = args.get("frontmatter")
        mode = args.get("mode", "create")
        
        result = await self._vault_manager.write_note(
            path=path,
            content=content,
            frontmatter=frontmatter,
            mode=mode
        )
        
        # Update index
        await self._index_engine.index_note(path)
        
        return {
            "success": True,
            "path": result.path,
            "operation": mode
        }
    
    async def _handle_search(self, args: Dict) -> Dict:
        """Search vault"""
        query = args["query"]
        mode = args.get("mode", "fulltext")
        limit = args.get("limit", 50)
        
        if self.enable_swarm and args.get("parallel", False):
            # Use swarm for parallel search
            return await self._swarm_coordinator.execute_search(
                query=query,
                pattern=args.get("swarm_pattern", "concurrent"),
                max_agents=args.get("max_agents", 5)
            )
        
        # Standard search
        results = await self._index_engine.search(
            query=query,
            mode=mode,
            limit=limit
        )
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    
    async def _handle_graph(self, args: Dict) -> Dict:
        """Graph operations"""
        operation = args.get("graph_operation", "subgraph")
        
        if operation == "subgraph":
            path = args.get("path")
            depth = args.get("depth", 2)
            graph = await self._index_engine.get_subgraph(path, depth)
            return {"success": True, "graph": graph}
        
        elif operation == "backlinks":
            path = args["path"]
            backlinks = await self._index_engine.get_backlinks(path)
            return {"success": True, "backlinks": backlinks}
        
        elif operation == "orphans":
            orphans = await self._index_engine.find_orphans()
            return {"success": True, "orphans": orphans}
        
        elif operation == "clusters":
            # Use swarm for cluster detection
            if self.enable_swarm:
                clusters = await self._swarm_coordinator.analyze_clusters(
                    algorithm=args.get("algorithm", "louvain")
                )
                return {"success": True, "clusters": clusters}
        
        return {"error": f"Unknown graph operation: {operation}"}
    
    async def _handle_swarm(self, args: Dict) -> Dict:
        """Execute swarm-based operations"""
        if not self.enable_swarm:
            return {"error": "Swarm operations not enabled"}
        
        swarm_type = args.get("swarm_type", "search")
        
        if swarm_type == "search":
            return await self._swarm_coordinator.execute_search(
                query=args["query"],
                pattern=args.get("pattern", "concurrent"),
                max_agents=args.get("max_agents", 5)
            )
        
        elif swarm_type == "analyze":
            return await self._swarm_coordinator.analyze_content(
                paths=args.get("paths", []),
                task=args["task"],
                pattern=args.get("pattern", "moa")
            )
        
        elif swarm_type == "graph":
            return await self._swarm_coordinator.analyze_graph(
                operation=args["operation"],
                pattern=args.get("pattern", "star")
            )
        
        elif swarm_type == "transform":
            return await self._swarm_coordinator.transform_notes(
                paths=args.get("paths", []),
                transformation=args["transformation"],
                pattern=args.get("pattern", "sequential")
            )
        
        return {"error": f"Unknown swarm type: {swarm_type}"}

    # Additional handler implementations...
    
    def get_parameters(self) -> Dict:
        """Return JSON schema for tool parameters"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "delete", "move", "search", "graph", 
                             "metadata", "template", "canvas", "vault", "swarm"],
                    "description": "Operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "Note path relative to vault root"
                },
                "content": {
                    "type": "string",
                    "description": "Content for write operations"
                },
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "parallel": {
                    "type": "boolean",
                    "description": "Use swarm parallel execution"
                },
                "swarm_pattern": {
                    "type": "string",
                    "enum": ["concurrent", "hierarchical", "moa", "star", "vote", 
                             "graph", "sequential"],
                    "description": "Swarm pattern to use"
                }
            },
            "required": ["operation"]
        }
```

#### 2.2.2 Swarm Coordinator

**File:** `/a0/python/helpers/obsidian_swarm.py`

```python
"""
Obsidian Swarm Coordinator - Parallel Processing Engine
Orchestrates swarm patterns for maximum parallel performance
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from python.helpers.swarm_orchestration import (
    AgentConfig,
    WorkflowResult,
    WorkflowStatus
)
from python.tools.swarm_workflow import (
    SequentialWorkflow,
    ConcurrentWorkflow,
    GraphWorkflow
)
from python.tools.swarm_consensus import (
    MajorityVoting,
    MixtureOfAgents
)
from python.tools.swarm_patterns import (
    StarSwarm,
    HierarchicalSwarm
)


class SwarmPattern(Enum):
    """Available swarm patterns for Obsidian operations"""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    GRAPH = "graph"
    VOTE = "vote"
    MOA = "moa"
    STAR = "star"
    HIERARCHICAL = "hierarchical"


@dataclass
class SwarmCoordinator:
    """
    Coordinates swarm-based operations for Obsidian vault.
    Selects optimal pattern based on operation type and executes
    with maximum parallelism.
    """
    
    vault_manager: Any  # VaultManager
    index_engine: Any  # IndexEngine
    cache_manager: Any  # CacheManager
    agent: Any = None  # Parent agent for spawning subordinates
    
    # Configuration
    max_concurrent_agents: int = 10
    default_timeout: int = 300
    
    # Pattern selection rules
    pattern_rules: Dict[str, SwarmPattern] = field(default_factory=lambda: {
        "search": SwarmPattern.CONCURRENT,
        "analyze": SwarmPattern.MOA,
        "graph": SwarmPattern.STAR,
        "transform": SwarmPattern.SEQUENTIAL,
        "validate": SwarmPattern.VOTE,
        "summarize": SwarmPattern.HIERARCHICAL
    })
    
    async def execute_search(
        self,
        query: str,
        pattern: str = "concurrent",
        max_agents: int = 5
    ) -> Dict[str, Any]:
        """
        Execute parallel search across vault.
        
        Pattern Selection:
        - concurrent: Parallel search agents for different sections
        - star: Hub coordinates search strategy
        - hierarchical: Multi-level search refinement
        """
        if pattern == "concurrent":
            return await self._search_concurrent(query, max_agents)
        elif pattern == "star":
            return await self._search_star(query, max_agents)
        elif pattern == "hierarchical":
            return await self._search_hierarchical(query, max_agents)
        else:
            return await self._search_concurrent(query, max_agents)
    
    async def _search_concurrent(self, query: str, max_agents: int) -> Dict:
        """
        Concurrent search pattern - parallel agents search different
        vault sections simultaneously.
        """
        # Get vault sections
        sections = await self.vault_manager.get_sections(max_agents)
        
        # Create agent configs for each section
        agents = []
        for i, section in enumerate(sections):
            agents.append(AgentConfig(
                name=f"search_agent_{i}",
                profile="researcher",
                prompt=f"""Search the vault section '{section}' for: {query}
                
                Return results with:
                - note_path
                - relevance_score
                - context_snippet
                """,
                timeout=60
            ))
        
        # Execute concurrent workflow
        workflow = ConcurrentWorkflow(
            agents=agents,
            aggregation="concat",
            max_concurrency=max_agents
        )
        
        result = await workflow.execute(initial_input=query)
        
        # Aggregate and rank results
        aggregated = await self._aggregate_search_results(result)
        
        return {
            "success": True,
            "pattern": "concurrent",
            "results": aggregated,
            "agents_used": len(agents)
        }
    
    async def _search_star(self, query: str, max_agents: int) -> Dict:
        """
        Star search pattern - hub coordinates, spokes execute.
        Hub decomposes query and aggregates results.
        """
        hub_config = AgentConfig(
            name="search_hub",
            profile="researcher",
            prompt="""You are the search coordinator.
            Decompose the search query into sub-queries for parallel execution.
            Then aggregate and rank results from search agents.
            """
        )
        
        spoke_configs = [
            AgentConfig(
                name=f"search_spoke_{i}",
                profile="researcher",
                prompt="Execute search in assigned vault section"
            )
            for i in range(max_agents)
        ]
        
        workflow = StarSwarm(
            agents=spoke_configs,
            hub_agent=hub_config,
            hub_timeout=120,
            spoke_timeout=60
        )
        
        result = await workflow.execute(task=query)
        
        return {
            "success": True,
            "pattern": "star",
            "results": result.final_output,
            "agents_used": max_agents + 1
        }
    
    async def analyze_content(
        self,
        paths: List[str],
        task: str,
        pattern: str = "moa"
    ) -> Dict[str, Any]:
        """
        Multi-agent content analysis.
        
        Pattern Selection:
        - moa: Mixture of Agents for diverse perspectives
        - vote: Consensus on analysis conclusions
        - hierarchical: Multi-level analysis (sections -> whole)
        """
        if pattern == "moa":
            return await self._analyze_moa(paths, task)
        elif pattern == "vote":
            return await self._analyze_vote(paths, task)
        elif pattern == "hierarchical":
            return await self._analyze_hierarchical(paths, task)
        else:
            return await self._analyze_moa(paths, task)
    
    async def _analyze_moa(self, paths: List[str], task: str) -> Dict:
        """
        Mixture of Agents pattern - diverse analyzers propose,
        aggregator synthesizes best analysis.
        """
        # Read content
        contents = await self._read_paths(paths)
        
        # Proposer agents with different perspectives
        proposers = [
            AgentConfig(
                name="structural_analyst",
                profile="researcher",
                prompt="""Analyze the content from a structural perspective.
                        Focus on: organization, hierarchy, relationships, patterns.
                        """
            ),
            AgentConfig(
                name="semantic_analyst",
                profile="researcher",
                prompt="""Analyze the content from a semantic perspective.
                        Focus on: meaning, themes, concepts, implications.
                        """
            ),
            AgentConfig(
                name="practical_analyst",
                profile="developer",
                prompt="""Analyze the content from a practical perspective.
                        Focus on: applicability, use cases, action items.
                        """
            ),
            AgentConfig(
                name="critical_analyst",
                profile="researcher",
                prompt="""Analyze the content critically.
                        Focus on: gaps, inconsistencies, areas for improvement.
                        """
            )
        ]
        
        # Aggregator agent
        aggregator = AgentConfig(
            name="analysis_synthesizer",
            profile="researcher",
            prompt="""Synthesize multiple analysis perspectives into a comprehensive answer.
                    Integrate insights, resolve conflicts, provide unified conclusion.
                    """
        )
        
        workflow = MixtureOfAgents(
            proposers=proposers,
            aggregator=aggregator,
            rounds=2  # Two refinement rounds
        )
        
        result = await workflow.execute(
            task=f"{task}\n\nContent:\n{contents}"
        )
        
        return {
            "success": True,
            "pattern": "moa",
            "analysis": result.final_output,
            "perspectives": len(proposers)
        }
    
    async def _analyze_vote(self, paths: List[str], task: str) -> Dict:
        """
        Voting pattern - multiple analysts vote on conclusions.
        Best for fact verification and consensus decisions.
        """
        contents = await self._read_paths(paths)
        
        agents = [
            AgentConfig(
                name=f"analyst_{i}",
                profile="researcher",
                prompt=f"Analyze and answer: {task}"
            )
            for i in range(5)
        ]
        
        workflow = MajorityVoting(
            agents=agents,
            voting_strategy="semantic",
            similarity_threshold=0.8
        )
        
        result = await workflow.execute(
            task=f"{task}\n\nContent:\n{contents}"
        )
        
        return {
            "success": True,
            "pattern": "vote",
            "consensus": result.final_output,
            "confidence": result.metadata.get("consensus_strength", 0)
        }
    
    async def analyze_graph(
        self,
        operation: str,
        pattern: str = "star"
    ) -> Dict[str, Any]:
        """
        Graph analysis with swarm patterns.
        
        Operations:
        - clusters: Detect note clusters
        - central_nodes: Find hub notes
        - paths: Analyze connection paths
        - summary: Overall graph statistics
        """
        if pattern == "star":
            return await self._graph_star(operation)
        elif pattern == "hierarchical":
            return await self._graph_hierarchical(operation)
        else:
            return await self._graph_star(operation)
    
    async def _graph_star(self, operation: str) -> Dict:
        """
        Star pattern for graph analysis.
        Hub coordinates, spokes analyze different graph aspects.
        """
        hub = AgentConfig(
            name="graph_coordinator",
            profile="researcher",
            prompt=f"""Coordinate graph analysis for: {operation}
            Delegate specific analysis tasks to spoke agents.
            Aggregate results into comprehensive graph report.
            """
        )
        
        spokes = [
            AgentConfig(
                name="cluster_analyst",
                profile="researcher",
                prompt="Detect and analyze note clusters"
            ),
            AgentConfig(
                name="centrality_analyst",
                profile="researcher",
                prompt="Analyze node centrality and identify hub notes"
            ),
            AgentConfig(
                name="path_analyst",
                profile="researcher",
                prompt="Analyze connection paths and note distances"
            )
        ]
        
        workflow = StarSwarm(
            agents=spokes,
            hub_agent=hub
        )
        
        # Get graph data
        graph_data = await self.index_engine.get_full_graph()
        
        result = await workflow.execute(
            task=f"Operation: {operation}\nGraph: {json.dumps(graph_data)}"
        )
        
        return {
            "success": True,
            "pattern": "star",
            "operation": operation,
            "result": result.final_output
        }
    
    async def transform_notes(
        self,
        paths: List[str],
        transformation: str,
        pattern: str = "sequential"
    ) -> Dict[str, Any]:
        """
        Transform notes with swarm patterns.
        
        Patterns:
        - sequential: Transform one by one with output chaining
        - concurrent: Transform all simultaneously
        - graph: Transform based on dependency graph
        """
        if pattern == "sequential":
            return await self._transform_sequential(paths, transformation)
        elif pattern == "concurrent":
            return await self._transform_concurrent(paths, transformation)
        elif pattern == "graph":
            return await self._transform_graph(paths, transformation)
        else:
            return await self._transform_concurrent(paths, transformation)
    
    async def _transform_concurrent(self, paths: List[str], transformation: str) -> Dict:
        """Concurrent transformation - all notes processed in parallel"""
        agents = [
            AgentConfig(
                name=f"transformer_{i}",
                profile="developer",
                prompt=f"""Transform the note according to: {transformation}
                
                Preserve:
                - Original metadata
                - Wikilinks to other notes
                - Note structure
                
                Return transformed content.
                """
            )
            for i in range(len(paths))
        ]
        
        workflow = ConcurrentWorkflow(
            agents=agents,
            aggregation="concat"
        )
        
        # Read all notes
        contents = await self._read_paths(paths)
        
        result = await workflow.execute(
            initial_input=[{"path": p, "content": c} for p, c in zip(paths, contents)]
        )
        
        # Write transformed notes
        transformed = result.final_output
        for item in transformed:
            await self.vault_manager.write_note(
                path=item["path"],
                content=item["content"],
                mode="overwrite"
            )
        
        return {
            "success": True,
            "pattern": "concurrent",
            "transformed": len(transformed)
        }
    
    async def _aggregate_search_results(self, result: WorkflowResult) -> List[Dict]:
        """Aggregate and deduplicate search results"""
        all_results = []
        seen_paths = set()
        
        for step in result.steps:
            if step.success:
                try:
                    results = json.loads(step.output)
                    for r in results.get("results", []):
                        path = r.get("note_path")
                        if path and path not in seen_paths:
                            seen_paths.add(path)
                            all_results.append(r)
                except:
                    continue
        
        # Sort by relevance
        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return all_results
    
    async def _read_paths(self, paths: List[str]) -> str:
        """Read multiple paths and return combined content"""
        contents = []
        for path in paths:
            note = await self.vault_manager.read_note(path)
            contents.append(f"### {path}\n\n{note.content}")
        return "\n\n---\n\n".join(contents)
```

### 2.3 Prompt Files for /a0/prompts/

#### 2.3.1 Tool Documentation

**File:** `/a0/prompts/default/tools/obsidian.md`

```markdown
# Obsidian Tool

## Description

Native Obsidian vault integration for Agent Zero. Provides comprehensive
access to notes, search, graph relationships, metadata, and templates with
full swarm pattern support for parallel processing.

## Operations

### Note Operations

#### `read`
Read a note or list notes in the vault.

```json
{
  "operation": "read",
  "path": "folder/note.md"
}
```

Parameters:
- `path` (string, optional): Note path relative to vault root
- `folder` (string, optional): List notes in folder
- `recursive` (boolean): List recursively (default: true)

#### `write`
Create or update a note.

```json
{
  "operation": "write",
  "path": "notes/new-note.md",
  "content": "# My Note\n\nContent here...",
  "frontmatter": {
    "tags": ["important", "reference"],
    "created": "2024-01-15"
  },
  "mode": "create"
}
```

Modes:
- `create`: Create new (error if exists)
- `overwrite`: Replace existing
- `append`: Add to end
- `prepend`: Add to beginning

#### `delete`
Delete a note.

```json
{
  "operation": "delete",
  "path": "notes/old-note.md",
  "trash": true
}
```

### Search Operations

#### `search`
Full-text search across the vault.

```json
{
  "operation": "search",
  "query": "machine learning algorithms",
  "mode": "fulltext",
  "limit": 20,
  "parallel": true,
  "swarm_pattern": "concurrent"
}
```

Search modes:
- `fulltext`: Standard full-text search
- `fuzzy`: Fuzzy matching for typos
- `regex`: Regular expression search
- `semantic`: Semantic similarity search

When `parallel: true`, uses swarm patterns for distributed search.

### Graph Operations

#### `graph`
Analyze link relationships.

```json
{
  "operation": "graph",
  "graph_operation": "subgraph",
  "path": "concepts/main-concept.md",
  "depth": 3
}
```

Graph operations:
- `subgraph`: Get connected notes around a center
- `backlinks`: Notes linking TO a note
- `forward_links`: Notes linked FROM a note
- `orphans`: Notes with no connections
- `clusters`: Detect note clusters

### Swarm Operations

#### `swarm`
Execute parallel operations with swarm patterns.

```json
{
  "operation": "swarm",
  "swarm_type": "analyze",
  "paths": ["note1.md", "note2.md", "note3.md"],
  "task": "Summarize key insights and identify common themes",
  "pattern": "moa"
}
```

Swarm patterns:
- `concurrent`: Parallel execution, concatenate results
- `sequential`: Chain execution, pass output forward
- `star`: Hub coordinates, spokes execute
- `hierarchical`: Multi-level decomposition
- `moa`: Mixture of Agents for diverse perspectives
- `vote`: Majority voting for consensus
- `graph`: Dependency-based execution

## Best Practices

### When to Use Swarm Patterns

| Operation | Recommended Pattern | Reason |
|-----------|-------------------|--------|
| Search large vault | `concurrent` | Parallel section search |
| Analyze multiple notes | `moa` | Diverse perspectives |
| Validate findings | `vote` | Consensus verification |
| Transform notes | `concurrent` | Parallel processing |
| Complex analysis | `hierarchical` | Multi-level decomposition |
| Graph analysis | `star` | Hub-spoke coordination |

### Performance Tips

1. **Large vaults (>10k notes)**: Enable caching and use parallel search
2. **Frequent searches**: Pre-index with `vault:reindex`
3. **Complex queries**: Use `semantic` mode with embeddings
4. **Batch operations**: Use swarm patterns with appropriate `max_agents`

## Examples

### Example 1: Daily Note Workflow

```json
{
  "operation": "template",
  "template_action": "daily",
  "date": "today",
  "template": "Templates/Daily Note.md"
}
```

### Example 2: Parallel Analysis

```json
{
  "operation": "swarm",
  "swarm_type": "analyze",
  "paths": ["Project Notes/*.md"],
  "task": "Identify action items and deadlines",
  "pattern": "hierarchical",
  "max_agents": 5
}
```

### Example 3: Graph Exploration

```json
{
  "operation": "graph",
  "graph_operation": "subgraph",
  "path": "Areas/Research/Main Topic.md",
  "depth": 2,
  "direction": "both"
}
```
```

### 2.4 Skill Files for /a0/usr/skills/

**File:** `/a0/usr/skills/obsidian/SKILL.md`

```markdown
# Obsidian Native Integration Skill

Skill for Obsidian vault operations with Agent Zero swarm capabilities.

## Overview

This skill provides comprehensive Obsidian vault integration with:
- Direct file system access to vaults
- Full-text and semantic search
- Graph analysis (backlinks, forward links, clusters)
- Metadata manipulation (frontmatter, tags)
- Template processing
- Canvas file support
- Swarm-based parallel operations

## Prerequisites

- Obsidian vault path configured in `OBSIDIAN_VAULT_PATH` environment variable
- Agent Zero framework with swarm tools installed
- Optional: Embeddings model for semantic search

## Quick Start

### Basic Note Operations

```python
# Read a note
result = obsidian(operation="read", path="Notes/My Note.md")

# Write a note
obsidian(
    operation="write",
    path="Notes/New Note.md",
    content="# Title\n\nContent",
    frontmatter={"tags": ["new"]}
)

# Search
results = obsidian(
    operation="search",
    query="project deadline",
    limit=10
)
```

### Parallel Operations with Swarm

```python
# Parallel search
results = obsidian(
    operation="search",
    query="machine learning",
    parallel=True,
    swarm_pattern="concurrent",
    max_agents=5
)

# Multi-perspective analysis
analysis = obsidian(
    operation="swarm",
    swarm_type="analyze",
    paths=["Research/*.md"],
    task="Identify key research themes and gaps",
    pattern="moa"
)

# Graph analysis
graph = obsidian(
    operation="swarm",
    swarm_type="graph",
    operation_type="clusters",
    pattern="star"
)
```

## Procedures

### P1: Vault Search and Retrieval

Use for finding notes across the vault.

1. Define search query and mode
2. Optionally enable parallel search for large vaults
3. Process and rank results

```python
# Standard search
results = obsidian(
    operation="search",
    query="API documentation",
    mode="fulltext",
    tags=["api", "docs"],
    limit=20
)

# Parallel search (recommended for vaults >5000 notes)
results = obsidian(
    operation="search",
    query="API documentation",
    parallel=True,
    swarm_pattern="concurrent"
)
```

### P2: Multi-Note Analysis

Use for analyzing multiple notes simultaneously.

1. Identify target notes (via search or explicit paths)
2. Define analysis task
3. Select swarm pattern based on needs
4. Execute and synthesize results

```python
# Find relevant notes first
notes = obsidian(
    operation="search",
    query="project requirements",
    limit=10
)

# Analyze with Mixture of Agents
analysis = obsidian(
    operation="swarm",
    swarm_type="analyze",
    paths=[n["path"] for n in notes["results"]],
    task="Extract and summarize all requirements mentioned",
    pattern="moa",
    max_agents=4
)
```

### P3: Graph Exploration

Use for understanding note relationships.

1. Start from a central note
2. Expand to related notes
3. Identify clusters and hubs

```python
# Get subgraph around a concept
subgraph = obsidian(
    operation="graph",
    graph_operation="subgraph",
    path="Concepts/Machine Learning.md",
    depth=3
)

# Find orphan notes
orphans = obsidian(
    operation="graph",
    graph_operation="orphans"
)

# Detect clusters
clusters = obsidian(
    operation="swarm",
    swarm_type="graph",
    operation_type="clusters",
    pattern="star"
)
```

### P4: Template Application

Use for creating standardized notes.

```python
# Apply template with variables
obsidian(
    operation="template",
    template_action="apply",
    template="Templates/Meeting Note.md",
    destination="Meetings/2024-01-15 Standup.md",
    variables={
        "date": "2024-01-15",
        "attendees": ["Alice", "Bob", "Charlie"],
        "meeting_type": "Standup"
    }
)

# Create daily note
obsidian(
    operation="template",
    template_action="daily",
    date="today"
)
```

### P5: Metadata Management

Use for working with frontmatter.

```python
# Get metadata
meta = obsidian(
    operation="metadata",
    metadata_action="get",
    path="Notes/Important.md"
)

# Update metadata
obsidian(
    operation="metadata",
    metadata_action="set",
    path="Notes/Important.md",
    metadata={
        "status": "reviewed",
        "priority": "high"
    },
    mode="merge"
)

# Get all tags
tags = obsidian(
    operation="metadata",
    metadata_action="tags"
)
```

### P6: Batch Transformation

Use for transforming multiple notes.

```python
# Transform notes in parallel
result = obsidian(
    operation="swarm",
    swarm_type="transform",
    paths=["Archive/Old Notes/*.md"],
    transformation="Convert all HTTP links to wikilinks where possible",
    pattern="concurrent"
)
```

## Swarm Pattern Selection Guide

| Task Type | Pattern | Max Agents | Use Case |
|-----------|---------|------------|----------|
| Search | `concurrent` | 5-10 | Parallel section search |
| Search | `star` | 5 | Coordinated search strategy |
| Analysis | `moa` | 4-6 | Diverse analytical perspectives |
| Analysis | `vote` | 5 | Consensus validation |
| Analysis | `hierarchical` | 3-5 | Multi-level decomposition |
| Transform | `concurrent` | 10 | Parallel batch processing |
| Transform | `sequential` | 1 | Ordered transformation chain |
| Graph | `star` | 3-5 | Coordinated graph analysis |
| Validate | `vote` | 5 | Consensus verification |

## Configuration

### Environment Variables

```bash
# Required
OBSIDIAN_VAULT_PATH=/path/to/vault

# Optional
OBSIDIAN_CACHE_SIZE=10000
OBSIDIAN_ENABLE_SWARM=true
OBSIDIAN_MAX_AGENTS=10
OBSIDIAN_INDEX_MODE=auto  # auto, sqlite, lancedb
```

### Vault Settings

Create `.obsidian/a0-config.json` in your vault:

```json
{
  "indexing": {
    "auto_reindex": true,
    "reindex_interval": 3600,
    "full_reindex_on_startup": false
  },
  "search": {
    "default_mode": "fulltext",
    "default_limit": 50,
    "parallel_threshold": 1000
  },
  "swarm": {
    "enabled": true,
    "default_pattern": "concurrent",
    "max_agents": 10
  },
  "templates": {
    "folder": "Templates",
    "daily_note_folder": "Daily Notes"
  }
}
```

## Troubleshooting

### Issue: Slow search on large vault

Solution: Enable parallel search with appropriate pattern:

```python
obsidian(
    operation="search",
    query="...",
    parallel=True,
    swarm_pattern="concurrent",
    max_agents=5
)
```

### Issue: Out of memory during batch operations

Solution: Reduce max_agents or use sequential pattern:

```python
obsidian(
    operation="swarm",
    swarm_type="transform",
    paths=[...],
    pattern="sequential"
)
```

### Issue: Index out of sync

Solution: Trigger reindex:

```python
obsidian(
    operation="vault",
    vault_action="reindex",
    full=True
)
```

## Files

```
/a0/usr/skills/obsidian/
├── SKILL.md                    # This file
├── scripts/
│   ├── quick_search.py         # Quick search utility
│   ├── batch_transform.py      # Batch transformation script
│   └── graph_export.py         # Graph export utilities
└── templates/
    ├── Daily Note.md
    ├── Meeting Note.md
    └── Project Note.md
```
```

---

## 3. Swarm Pattern Integration

### 3.1 Pattern Selection Matrix

The following matrix defines which swarm patterns are used for which Obsidian operations:

| Operation | Primary Pattern | Secondary Pattern | Concurrency | Notes |
|-----------|----------------|-------------------|-------------|-------|
| **Single Note Read** | Direct | - | 1 | No swarm needed |
| **Multi-Note Read** | `concurrent` | - | 5-10 | Parallel reads |
| **Note Write** | Direct | - | 1 | Single write |
| **Batch Write** | `concurrent` | `sequential` | 10 | Parallel writes |
| **Full-text Search** | `concurrent` | `star` | 5-10 | Section-based parallel |
| **Semantic Search** | `concurrent` | `hierarchical` | 5 | Embedding parallel |
| **Tag Search** | `concurrent` | - | 3 | Parallel filter |
| **Backlinks** | `concurrent` | - | 3 | Parallel resolution |
| **Graph Subgraph** | `star` | - | 3-5 | Hub-spoke coordination |
| **Graph Clusters** | `star` | `hierarchical` | 5 | Multi-level analysis |
| **Orphan Detection** | `concurrent` | - | 3 | Parallel scan |
| **Content Analysis** | `moa` | `vote` | 4-6 | Diverse perspectives |
| **Summary Generation** | `hierarchical` | `moa` | 3-5 | Multi-level synthesis |
| **Validation** | `vote` | - | 5 | Consensus verification |
| **Template Apply** | `sequential` | - | 1 | Variable substitution chain |
| **Batch Transform** | `concurrent` | `graph` | 10 | Parallel transformation |
| **Metadata Update** | `concurrent` | - | 5 | Parallel frontmatter updates |
| **Vault Reindex** | `hierarchical` | `star` | 5-10 | Coordinated indexing |

### 3.2 Parallel Execution Strategies

#### 3.2.1 Concurrent Pattern Strategy

**Use Case:** Parallel operations on independent items

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONCURRENT EXECUTION                         │
└─────────────────────────────────────────────────────────────────┘

Input: [note1.md, note2.md, note3.md, note4.md, note5.md]
                          │
                          ▼
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌────────┐        ┌────────┐        ┌────────┐
   │ Agent 1│        │ Agent 2│        │ Agent 3│
   │note1,2 │        │note3,4 │        │ note5  │
   └────────┘        └────────┘        └────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                   ┌────────────┐
                   │ Aggregator │
                   │ (concat)   │
                   └────────────┘
                          │
                          ▼
              Output: Combined Results
```

**Implementation:**

```python
async def concurrent_search(query: str, sections: List[str]) -> List[Result]:
    """Parallel search across vault sections"""
    
    agents = [
        AgentConfig(
            name=f"search_section_{i}",
            profile="researcher",
            prompt=f"Search section '{section}' for: {query}"
        )
        for i, section in enumerate(sections)
    ]
    
    workflow = ConcurrentWorkflow(
        agents=agents,
        aggregation="concat",
        max_concurrency=len(agents)
    )
    
    result = await workflow.execute(initial_input=query)
    return aggregate_results(result)
```

#### 3.2.2 Star Pattern Strategy

**Use Case:** Hub-coordinated operations with specialized spokes

```
┌─────────────────────────────────────────────────────────────────┐
│                       STAR EXECUTION                             │
└─────────────────────────────────────────────────────────────────┘

                    ┌────────────────┐
                    │   HUB AGENT    │
                    │  (Coordinator) │
                    │                │
                    │ - Decompose    │
                    │ - Distribute   │
                    │ - Aggregate    │
                    └───────┬────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │  SPOKE 1 │      │  SPOKE 2 │      │  SPOKE 3 │
   │  Search  │      │  Index   │      │  Graph   │
   │  Agent   │      │  Agent   │      │  Agent   │
   └──────────┘      └──────────┘      └──────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  HUB AGENT    │
                    │  (Synthesis)  │
                    └───────────────┘
                            │
                            ▼
                     Final Result
```

**Implementation:**

```python
async def star_graph_analysis(operation: str) -> Dict:
    """Hub-coordinated graph analysis"""
    
    hub = AgentConfig(
        name="graph_coordinator",
        profile="researcher",
        prompt="Coordinate graph analysis, synthesize results"
    )
    
    spokes = [
        AgentConfig(name="cluster_agent", profile="researcher",
                   prompt="Detect note clusters"),
        AgentConfig(name="centrality_agent", profile="researcher",
                   prompt="Analyze node centrality"),
        AgentConfig(name="path_agent", profile="researcher",
                   prompt="Analyze connection paths")
    ]
    
    workflow = StarSwarm(
        agents=spokes,
        hub_agent=hub,
        hub_timeout=120,
        spoke_timeout=60
    )
    
    result = await workflow.execute(task=operation)
    return result.final_output
```

#### 3.2.3 Hierarchical Pattern Strategy

**Use Case:** Multi-level decomposition and synthesis

```
┌─────────────────────────────────────────────────────────────────┐
│                   HIERARCHICAL EXECUTION                         │
└─────────────────────────────────────────────────────────────────┘

                          ┌─────────────┐
                          │ ROOT AGENT  │
                          │  (Analyst)  │
                          └──────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
             ┌───────────┐ ┌───────────┐ ┌───────────┐
             │ MANAGER 1 │ │ MANAGER 2 │ │ MANAGER 3 │
             │ (Folder A)│ │ (Folder B)│ │ (Folder C)│
             └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                   │             │             │
         ┌─────────┼───┐   ┌─────┼─────┐   ┌───┼─────────┐
         │         │   │   │     │     │   │   │         │
         ▼         ▼   ▼   ▼     ▼     ▼   ▼   ▼         ▼
      ┌────┐   ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
      │W1.1│   │W1.2│ │W2.1│ │W2.2│ │W3.1│ │W3.2│ │... │ │    │
      └────┘   └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
         │         │       │         │       │         │
         └─────────┴───────┴─────────┴───────┴─────────┘
                                 │
                                 ▼
                         ┌─────────────┐
                         │ AGGREGATION │
                         │  (Root)     │
                         └─────────────┘
```

**Implementation:**

```python
async def hierarchical_vault_analysis() -> Dict:
    """Multi-level vault analysis"""
    
    root = AgentConfig(
        name="vault_analyst",
        profile="researcher",
        prompt="Analyze overall vault, synthesize folder analyses"
    )
    
    managers = [
        AgentConfig(name="folder_a_manager", profile="researcher",
                   prompt="Analyze Folder A content"),
        AgentConfig(name="folder_b_manager", profile="researcher",
                   prompt="Analyze Folder B content"),
        AgentConfig(name="folder_c_manager", profile="researcher",
                   prompt="Analyze Folder C content")
    ]
    
    workers = {
        "folder_a_manager": [
            AgentConfig(name="a_worker_1", profile="researcher"),
            AgentConfig(name="a_worker_2", profile="researcher")
        ],
        "folder_b_manager": [
            AgentConfig(name="b_worker_1", profile="researcher"),
            AgentConfig(name="b_worker_2", profile="researcher")
        ],
        "folder_c_manager": [
            AgentConfig(name="c_worker_1", profile="researcher")
        ]
    }
    
    workflow = HierarchicalSwarm(
        root=root,
        managers=managers,
        workers=workers,
        max_concurrency=10
    )
    
    result = await workflow.execute(task="Comprehensive vault analysis")
    return result.final_output
```

#### 3.2.4 MoA Pattern Strategy

**Use Case:** Diverse expert perspectives with synthesis

```
┌─────────────────────────────────────────────────────────────────┐
│               MIXTURE OF AGENTS EXECUTION                        │
└─────────────────────────────────────────────────────────────────┘

Round 1:
         ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
         │  PROPOSER 1    │  │  PROPOSER 2    │  │  PROPOSER 3    │
         │  (Structural)  │  │  (Semantic)    │  │  (Critical)    │
         └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     ▼
                              ┌────────────┐
                              │ PROPOSALS  │
                              │  [P1, P2, P3] │
                              └────────────┘
                                     │
Round 2:                             │
                                     ▼
         ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
         │  PROPOSER 1    │  │  PROPOSER 2    │  │  PROPOSER 3    │
         │ (Refined)      │  │ (Refined)      │  │ (Refined)      │
         │ sees P2, P3    │  │ sees P1, P3    │  │ sees P1, P2    │
         └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     ▼
                              ┌────────────┐
                              │ AGGREGATOR │
              ▶               │            │
                              └────────────┘
                                     │
                                     ▼
                             FINAL ANSWER
```

**Implementation:**

```python
async def moa_content_analysis(paths: List[str], task: str) -> Dict:
    """Multi-perspective content analysis"""
    
    contents = await read_notes(paths)
    
    proposers = [
        AgentConfig(
            name="structural_analyst",
            profile="researcher",
            prompt="Analyze structure, organization, patterns"
        ),
        AgentConfig(
            name="semantic_analyst",
            profile="researcher",
            prompt="Analyze meaning, themes, concepts"
        ),
        AgentConfig(
            name="practical_analyst",
            profile="developer",
            prompt="Analyze applicability, use cases, actions"
        ),
        AgentConfig(
            name="critical_analyst",
            profile="researcher",
            prompt="Analyze gaps, inconsistencies, improvements"
        )
    ]
    
    aggregator = AgentConfig(
        name="synthesis_agent",
        profile="researcher",
        prompt="Synthesize diverse perspectives into unified analysis"
    )
    
    workflow = MixtureOfAgents(
        proposers=proposers,
        aggregator=aggregator,
        rounds=2
    )
    
    result = await workflow.execute(
        task=f"{task}\n\nContent:\n{contents}"
    )
    
    return {
        "analysis": result.final_output,
        "perspectives": len(proposers),
        "rounds": 2
    }
```

#### 3.2.5 Vote Pattern Strategy

**Use Case:** Consensus verification and fact checking

```
┌─────────────────────────────────────────────────────────────────┐
│                     VOTING EXECUTION                             │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │      INPUT TASK         │
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
   ┌──────────┐          ┌──────────┐          ┌──────────┐
   │ AGENT 1  │          │ AGENT 2  │          │ AGENT N  │
   │          │          │          │          │          │
   │ Answer A │          │ Answer A │          │ Answer B │
   └────┬─────┘          └────┬─────┘          └────┬─────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  VOTE COUNTING  │
                    │                 │
                    │  A: 2 votes     │
                    │  B: 1 vote      │
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ WINNER: A       │
                    │ (Majority)      │
                    └─────────────────┘
```

**Implementation:**

```python
async def vote_validation(statement: str, paths: List[str]) -> Dict:
    """Consensus validation of statement against notes"""
    
    contents = await read_notes(paths)
    
    agents = [
        AgentConfig(
            name=f"validator_{i}",
            profile="researcher",
            prompt="Verify statement against provided content"
        )
        for i in range(5)
    ]
    
    workflow = MajorityVoting(
        agents=agents,
        voting_strategy="semantic",
        similarity_threshold=0.8,
        tie_break="llm"
    )
    
    result = await workflow.execute(
        task=f"Validate: {statement}\n\nEvidence:\n{contents}"
    )
    
    return {
        "consensus": result.final_output,
        "confidence": result.metadata.get("consensus_strength"),
        "voting_strategy": "semantic"
    }
```

### 3.3 Maximum Concurrency Configurations

```python
# /a0/python/helpers/obsidian_config.py

from dataclasses import dataclass

@dataclass
class ObsidianSwarmConfig:
    """Configuration for swarm-based operations"""
    
    # Concurrency limits
    max_concurrent_agents: int = 10
    max_search_agents: int = 8
    max_analysis_agents: int = 6
    max_transform_agents: int = 10
    
    # Timeouts (seconds)
    default_timeout: int = 300
    search_timeout: int = 60
    analysis_timeout: int = 120
    transform_timeout: int = 180
    
    # Pattern defaults
    default_search_pattern: str = "concurrent"
    default_analysis_pattern: str = "moa"
    default_graph_pattern: str = "star"
    default_transform_pattern: str = "concurrent"
    
    # MoA specific
    moa_rounds: int = 2
    moa_proposers: int = 4
    
    # Vote specific
    vote_agents: int = 5
    vote_threshold: float = 0.8
    
    # Hierarchical specific
    hierarchical_managers: int = 3
    hierarchical_workers_per_manager: int = 3
    
    # Star specific
    star_spokes: int = 5
    hub_timeout: int = 120
    spoke_timeout: int = 60
    
    # Queue management
    max_queue_size: int = 100
    queue_timeout: int = 600
```

---

## 4. Implementation Phases

### Phase 1: Foundation (MCP + File Access)
**Duration:** 3-4 days

#### Objectives
- Establish MCP server for Obsidian
- Implement direct vault file access
- Create basic indexing infrastructure

#### Deliverables

| File | Description | Status |
|------|-------------|--------|
| `/a0/python/tools/obsidian_mcp_server.py` | MCP server implementation | TODO |
| `/a0/python/helpers/obsidian_vault.py` | Vault manager class | TODO |
| `/a0/python/helpers/obsidian_index.py` | Basic index engine | TODO |
| `/a0/python/helpers/obsidian_cache.py` | LRU cache manager | TODO |
| `/a0/prompts/default/tools/obsidian_mcp_server.md` | MCP tool docs | TODO |

#### Tasks

1. **Day 1: MCP Server Setup**
   - Create ObsidianMCPServer class
   - Define tool schemas for basic operations
   - Implement stdio transport
   
2. **Day 2: Vault Manager**
   - Implement VaultManager class
   - Direct file system access
   - Note parsing (frontmatter, content, links)
   - Write operations with atomic file handling
   
3. **Day 3: Index Engine**
   - SQLite-based full-text index
   - Wikilink extraction and resolution
   - Tag indexing
   - Basic search functionality
   
4. **Day 4: Integration & Testing**
   - Integrate MCP server with VaultManager
   - Basic integration tests
   - Performance benchmarking

#### Acceptance Criteria
- MCP server starts and responds to tool calls
- Can read, write, list notes through MCP
- Basic search returns results within 500ms for 10k notes
- Cache improves repeated read performance by 10x

### Phase 2: Core Operations (CRUD + Search)
**Duration:** 4-5 days

#### Objectives
- Complete CRUD operations
- Advanced search capabilities
- Graph relationship tracking
- Metadata management

#### Deliverables

| File | Description | Status |
|------|-------------|--------|
| `/a0/python/tools/obsidian.py` | Main tool class | TODO |
| `/a0/python/helpers/obsidian_watcher.py` | File watcher service | TODO |
| `/a0/python/helpers/obsidian_lock.py` | Lock manager | TODO |
| `/a0/prompts/default/tools/obsidian.md` | Tool documentation | TODO |

#### Tasks

1. **Day 1-2: Complete CRUD**
   - Note update with modes (overwrite, append, prepend)
   - Note delete with trash support
   - Note move with link updating
   - Batch operations
   
2. **Day 3: Advanced Search**
   - Fuzzy search
   - Regex search
   - Tag-based filtering
   - Date range filtering
   - Combined filters
   
3. **Day 4: Graph Operations**
   - Backlink tracking
   - Forward link resolution
   - Orphan detection
   - Subgraph extraction
   
4. **Day 5: Metadata Management**
   - Frontmatter parsing (YAML)
   - Metadata CRUD
   - Tag management
   - Property inheritance

#### Acceptance Criteria
- All CRUD operations work correctly
- Search supports all modes with <200ms latency
- Graph operations complete in <1s for 10k notes
- Metadata updates preserve note integrity

### Phase 3: Advanced Features (Graph, Metadata, Templates)
**Duration:** 4-5 days

#### Objectives
- Semantic search with embeddings
- Template system
- Canvas file support
- Advanced graph analysis

#### Deliverables

| File | Description | Status |
|------|-------------|--------|
| `/a0/python/helpers/obsidian_embeddings.py` | Embedding engine | TODO |
| `/a0/python/helpers/obsidian_templates.py` | Template engine | TODO |
| `/a0/python/helpers/obsidian_canvas.py` | Canvas support | TODO |
| `/a0/python/helpers/obsidian_graph.py` | Graph analysis | TODO |
| `/a0/usr/skills/obsidian/SKILL.md` | Skill definition | TODO |

#### Tasks

1. **Day 1-2: Semantic Search**
   - Embedding generation pipeline
   - LanceDB integration for vector search
   - Hybrid search (fulltext + semantic)
   - Result reranking
   
2. **Day 3: Template System**
   - Template parsing (Jinja2)
   - Variable substitution
   - Daily notes integration
   - Template inheritance
   
3. **Day 4: Canvas Support**
   - Canvas file format parsing
   - Node types (text, file, link)
   - Edge handling
   - Canvas creation/modification
   
4. **Day 5: Advanced Graph**
   - Community detection (Louvain)
   - Centrality measures
   - Path finding
   - Graph visualization data

#### Acceptance Criteria
- Semantic search provides relevant results
- Templates generate correct notes
- Canvas files are readable and writable
- Graph analysis identifies clusters correctly

### Phase 4: Swarm Integration (Parallel Processing)
**Duration:** 5-6 days

#### Objectives
- Integrate all swarm patterns
- Parallel search implementation
- Multi-agent analysis
- Batch transformation pipelines

#### Deliverables

| File | Description | Status |
|------|-------------|--------|
| `/a0/python/helpers/obsidian_swarm.py` | Swarm coordinator | TODO |
| `/a0/prompts/default/tools/obsidian_swarm.md` | Swarm docs | TODO |
| `/a0/python/tools/obsidian_swarm_tools.py` | Additional swarm tools | TODO |

#### Tasks

1. **Day 1-2: Swarm Coordinator**
   - SwarmCoordinator class implementation
   - Pattern selection logic
   - Agent configuration management
   - Result aggregation
   
2. **Day 3: Parallel Search**
   - Concurrent search pattern
   - Star search pattern
   - Hierarchical search pattern
   - Performance optimization
   
3. **Day 4: Multi-Agent Analysis**
   - MoA pattern for analysis
   - Vote pattern for validation
   - Hierarchical pattern for synthesis
   
4. **Day 5: Batch Transformation**
   - Concurrent transformation pattern
   - Graph-based dependency transformation
   - Sequential transformation chain
   
5. **Day 6: Integration Testing**
   - End-to-end swarm tests
   - Performance benchmarks
   - Error handling verification

#### Acceptance Criteria
- All 7 swarm patterns work for appropriate operations
- Parallel search 5x faster than sequential for large vaults
- MoA produces comprehensive multi-perspective analyses
- Batch transformation handles 100+ notes correctly

### Phase 5: Native Integration (Embedded in Agent Zero Core)
**Duration:** 3-4 days

#### Objectives
- Embed in Agent Zero core
- Update system prompts
- Create comprehensive documentation
- Production-ready deployment

#### Deliverables

| File | Description | Status |
|------|-------------|--------|
| `/a0/prompts/default/agent.system.md` | Updated system prompt | TODO |
| `/a0/docs/obsidian_integration.md` | Integration documentation | TODO |
| `/a0/tests/test_obsidian.py` | Comprehensive test suite | TODO |
| `/a0/scripts/obsidian_setup.py` | Setup script | TODO |

#### Tasks

1. **Day 1: Core Integration**
   - Register tools in Agent Zero tool registry
   - Update system prompts to include Obsidian
   - Configuration management
   
2. **Day 2: Documentation**
   - API documentation
   - Usage examples
   - Architecture documentation
   - Configuration guide
   
3. **Day 3: Testing**
   - Unit tests for all components
   - Integration tests
   - Performance tests
   - Edge case handling
   
4. **Day 4: Deployment**
   - Setup script
   - Environment configuration
   - Vault initialization
   - Production checks

#### Acceptance Criteria
- Obsidian tools available by default in Agent Zero
- Documentation covers all features
- Test coverage >90%
- Setup completes in <5 minutes

---

## 5. File Structure

### 5.1 Complete File Tree

```
/a0/
├── python/
│   ├── tools/
│   │   ├── obsidian.py                    # Main Obsidian tool
│   │   ├── obsidian_mcp_server.py        # MCP server implementation
│   │   └── obsidian_swarm_tools.py        # Additional swarm tools
│   │
│   └── helpers/
│       ├── obsidian_vault.py             # Vault management
│       ├── obsidian_index.py             # Index engine
│       ├── obsidian_cache.py             # Cache management
│       ├── obsidian_watcher.py           # File watching
│       ├── obsidian_lock.py              # Lock management
│       ├── obsidian_swarm.py             # Swarm coordinator
│       ├── obsidian_embeddings.py        # Embedding engine
│       ├── obsidian_templates.py         # Template processing
│       ├── obsidian_canvas.py            # Canvas support
│       ├── obsidian_graph.py             # Graph analysis
│       ├── obsidian_export.py            # Export utilities
│       ├── obsidian_sync.py              # Multi-vault sync
│       └── obsidian_config.py            # Configuration
│
├── prompts/
│   └── default/
│       └── tools/
│           ├── obsidian.md               # Tool documentation
│           ├── obsidian_mcp_server.md    # MCP server docs
│           └── obsidian_swarm.md         # Swarm integration docs
│
├── usr/
│   └── skills/
│       └── obsidian/
│           ├── SKILL.md                  # Skill definition
│           ├── scripts/
│           │   ├── quick_search.py       # Quick search utility
│           │   ├── batch_transform.py    # Batch transformation
│           │   └── graph_export.py       # Graph export
│           └── templates/
│               ├── Daily Note.md
│               ├── Meeting Note.md
│               └── Project Note.md
│
├── tests/
│   ├── test_obsidian.py                  # Main test suite
│   ├── test_obsidian_mcp.py              # MCP tests
│   ├── test_obsidian_swarm.py            # Swarm tests
│   └── fixtures/
│       └── test_vault/                   # Test vault
│           ├── note1.md
│           ├── note2.md
│           └── .obsidian/
│               └── app.json
│
├── docs/
│   └── obsidian_integration.md           # Integration guide
│
└── scripts/
    └── obsidian_setup.py                # Setup script
```

### 5.2 Module Responsibilities

#### `/a0/python/tools/obsidian.py`
```python
"""
Main Obsidian tool class.
Responsibilities:
- Tool interface implementation
- Operation routing
- Swarm integration
- Error handling
"""

class ObsidianTool(Tool):
    async def execute(self, **kwargs) -> Dict
    async def _handle_read(self, args) -> Dict
    async def _handle_write(self, args) -> Dict
    async def _handle_search(self, args) -> Dict
    async def _handle_graph(self, args) -> Dict
    async def _handle_swarm(self, args) -> Dict
```

#### `/a0/python/helpers/obsidian_vault.py`
```python
"""
Vault file system management.
Responsibilities:
- Direct file access
- Note parsing
- Atomic writes
- Path resolution
"""

class VaultManager:
    async def initialize(self)
    async def read_note(self, path: str) -> Note
    async def write_note(self, path: str, content: str, ...) -> WriteResult
    async def delete_note(self, path: str, trash: bool) -> None
    async def move_note(self, source: str, dest: str) -> MoveResult
    async def list_notes(self, folder: str, recursive: bool) -> List[str]
    async def get_sections(self, count: int) -> List[str]
```

#### `/a0/python/helpers/obsidian_index.py`
```python
"""
Search index management.
Responsibilities:
- Full-text indexing
- Wikilink indexing
- Tag indexing
- Metadata indexing
"""

class IndexEngine:
    async def initialize(self)
    async def index_note(self, path: str) -> None
    async def remove_note(self, path: str) -> None
    async def search(self, query: str, mode: str, ...) -> List[SearchResult]
    async def get_backlinks(self, path: str) -> List[str]
    async def get_forward_links(self, path: str) -> List[str]
    async def get_subgraph(self, path: str, depth: int) -> Graph
    async def find_orphans(self) -> List[str]
```

#### `/a0/python/helpers/obsidian_swarm.py`
```python
"""
Swarm pattern coordination.
Responsibilities:
- Pattern selection
- Agent configuration
- Parallel execution
- Result aggregation
"""

class SwarmCoordinator:
    async def execute_search(self, query: str, pattern: str, ...) -> Dict
    async def analyze_content(self, paths: List[str], task: str, ...) -> Dict
    async def analyze_graph(self, operation: str, ...) -> Dict
    async def transform_notes(self, paths: List[str], ...) -> Dict
```

---

## 6. Configuration

### 6.1 Environment Variables

```bash
# === Required ===
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault

# === Optional ===
# Cache settings
OBSIDIAN_CACHE_SIZE=10000
OBSIDIAN_CACHE_TTL=3600

# Swarm settings
OBSIDIAN_ENABLE_SWARM=true
OBSIDIAN_MAX_AGENTS=10
OBSIDIAN_DEFAULT_PATTERN=concurrent

# Index settings
OBSIDIAN_INDEX_MODE=auto          # auto, sqlite, lancedb, hybrid
OBSIDIAN_INDEX_PATH=.obsidian/a0-index
OBSIDIAN_AUTO_REINDEX=true
OBSIDIAN_REINDEX_INTERVAL=3600

# Search settings
OBSIDIAN_SEARCH_MODE=fulltext     # fulltext, semantic, hybrid
OBSIDIAN_SEARCH_LIMIT=50
OBSIDIAN_PARALLEL_THRESHOLD=1000

# Embedding settings (for semantic search)
OBSIDIAN_EMBEDDING_MODEL=all-MiniLM-L6-v2
OBSIDIAN_EMBEDDING_DIMENSION=384

# Performance
OBSIDIAN_MAX_WORKERS=4
OBSIDIAN_BATCH_SIZE=100

# Logging
OBSIDIAN_LOG_LEVEL=INFO
OBSIDIAN_LOG_FILE=/var/log/a0/obsidian.log
```

### 6.2 Vault Configuration

**File:** `<vault>/.obsidian/a0-config.json`

```json
{
  "version": "1.0.0",
  "indexing": {
    "auto_reindex": true,
    "reindex_interval": 3600,
    "full_reindex_on_startup": false,
    "index_metadata": true,
    "index_links": true,
    "index_tags": true
  },
  "search": {
    "default_mode": "fulltext",
    "default_limit": 50,
    "parallel_threshold": 1000,
    "highlight_results": true,
    "snippet_length": 200
  },
  "swarm": {
    "enabled": true,
    "default_pattern": "concurrent",
    "max_agents": 10,
    "timeout": 300,
    "patterns": {
      "search": "concurrent",
      "analyze": "moa",
      "graph": "star",
      "transform": "concurrent",
      "validate": "vote"
    }
  },
  "templates": {
    "folder": "Templates",
    "daily_note_folder": "Daily Notes",
    "daily_note_format": "YYYY-MM-DD.md",
    "default_template": null
  },
  "graph": {
    "exclude_folders": [".trash", "Archive"],
    "exclude_patterns": ["*.canvas"],
    "max_depth": 5
  },
  "metadata": {
    "auto_created": true,
    "auto_modified": true,
    "auto_tags": true,
    "required_fields": []
  },
  "performance": {
    "cache_size": 10000,
    "batch_size": 100,
    "max_workers": 4
  }
}
```

### 6.3 Agent Zero Integration

**Update to:** `/a0/prompts/default/agent.system.md`

```markdown
## Obsidian Integration

You have native access to Obsidian vault functionality through the `obsidian` tool.
This provides:

1. **Note Management**: Read, write, delete, move notes
2. **Search**: Full-text, semantic, and tag-based search
3. **Graph Analysis**: Backlinks, forward links, clusters, orphans
4. **Metadata**: Frontmatter and tag management
5. **Templates**: Apply templates, create daily notes
6. **Swarm Operations**: Parallel processing for large-scale operations

### When to Use Swarm Patterns

- **concurrent**: Parallel search, batch operations
- **star**: Coordinated analysis, graph operations
- **hierarchical**: Multi-level vault analysis
- **moa**: Multi-perspective content analysis
- **vote**: Consensus validation
- **sequential**: Ordered transformations
- **graph**: Dependency-based operations

### Example Usage

```
# Quick search
obsidian(operation="search", query="project timeline")

# Parallel search for large vault
obsidian(
    operation="search",
    query="meeting notes",
    parallel=True,
    swarm_pattern="concurrent"
)

# Multi-perspective analysis
obsidian(
    operation="swarm",
    swarm_type="analyze",
    paths=["Project/*.md"],
    task="Extract action items and deadlines",
    pattern="moa"
)
```
```

### 6.4 Security Configuration

```json
{
  "security": {
    "read_only_mode": false,
    "allowed_folders": [],
    "denied_folders": [".trash", ".obsidian"],
    "max_file_size": 10485760,
    "allowed_extensions": [".md", ".canvas"],
    "sandbox_mode": false,
    "audit_logging": true,
    "audit_log_path": ".obsidian/a0-audit.log"
  }
}
```

---

## 7. API Reference

### 7.1 Tool Operations

#### `read`

**Purpose:** Read notes from vault

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| path | string | no* | - | Note path to read |
| folder | string | no | "" | Folder to list (if no path) |
| recursive | boolean | no | true | List recursively |

*Either `path` or `folder` required

**Returns:**
```json
{
  "success": true,
  "note": {
    "path": "Notes/Example.md",
    "content": "# Example Note\n\nContent here...",
    "metadata": {"tags": ["example"]},
    "links": ["[[Related Note]]"]
  }
}
```

#### `write`

**Purpose:** Create or update notes

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| path | string | yes | - | Note path |
| content | string | yes | - | Note content |
| frontmatter | object | no | null | YAML frontmatter |
| mode | string | no | "create" | create/overwrite/append/prepend |

**Returns:**
```json
{
  "success": true,
  "path": "Notes/New.md",
  "operation": "create"
}
```

#### `search`

**Purpose:** Search vault content

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | yes | - | Search query |
| mode | string | no | "fulltext" | fulltext/fuzzy/regex/semantic |
| tags | array | no | [] | Filter by tags |
| limit | integer | no | 50 | Max results |
| parallel | boolean | no | false | Use swarm pattern |
| swarm_pattern | string | no | "concurrent" | Swarm pattern to use |

**Returns:**
```json
{
  "success": true,
  "results": [
    {
      "path": "Notes/Result.md",
      "score": 0.95,
      "snippet": "...matching content...",
      "metadata": {"tags": ["relevant"]}
    }
  ],
  "count": 1
}
```

#### `graph`

**Purpose:** Graph operations

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| graph_operation | string | yes | - | subgraph/backlinks/forward_links/orphans/clusters |
| path | string | no* | - | Center note (for subgraph) |
| depth | integer | no | 2 | Subgraph depth |

**Returns:**
```json
{
  "success": true,
  "graph": {
    "nodes": [{"id": "Note A", "type": "note"}],
    "edges": [{"source": "Note A", "target": "Note B"}]
  }
}
```

#### `swarm`

**Purpose:** Parallel operations with swarm patterns

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| swarm_type | string | yes | - | search/analyze/graph/transform |
| query/task | string | yes* | - | Query or task description |
| paths | array | no | [] | Notes to process |
| pattern | string | no | "concurrent" | Swarm pattern |
| max_agents | integer | no | 5 | Max parallel agents |

**Returns:**
```json
{
  "success": true,
  "pattern": "moa",
  "result": "...analysis output...",
  "agents_used": 4,
  "execution_time": 12.5
}
```

---

## 8. Security Considerations

### 8.1 Access Control

```python
# /a0/python/helpers/obsidian_security.py

from pathlib import Path
from typing import List, Optional
import fnmatch

class SecurityManager:
    """Manages access control for Obsidian operations"""
    
    def __init__(self, config: dict):
        self.read_only = config.get("read_only_mode", False)
        self.allowed_folders = config.get("allowed_folders", [])
        self.denied_folders = config.get("denied_folders", [])
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)
        self.allowed_extensions = config.get("allowed_extensions", [".md", ".canvas"])
    
    def check_read_access(self, path: Path) -> bool:
        """Verify read access to path"""
        # Check extension
        if path.suffix not in self.allowed_extensions:
            return False
        
        # Check denied folders
        for denied in self.denied_folders:
            if str(path).startswith(denied):
                return False
        
        # Check allowed folders (if specified)
        if self.allowed_folders:
            for allowed in self.allowed_folders:
                if str(path).startswith(allowed):
                    return True
            return False
        
        return True
    
    def check_write_access(self, path: Path) -> bool:
        """Verify write access to path"""
        if self.read_only:
            return False
        return self.check_read_access(path)
    
    def sanitize_content(self, content: str) -> str:
        """Sanitize note content for security"""
        # Remove potential script injections
        # Validate wikilinks
        # Check for malicious patterns
        return content
```

### 8.2 Audit Logging

```python
class AuditLogger:
    """Logs all Obsidian operations for audit"""
    
    def log_operation(
        self,
        operation: str,
        path: str,
        success: bool,
        agent: str,
        metadata: dict = None
    ):
        """Log an operation"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "path": path,
            "success": success,
            "agent": agent,
            "metadata": metadata or {}
        }
        # Write to audit log
```

### 8.3 Data Protection

- **Encryption at rest**: Optional vault encryption
- **Encryption in transit**: TLS for MCP connections
- **Credential management**: Environment variable secrets
- **Backup**: Automated vault backup before modifications

---

## 9. Testing Strategy

### 9.1 Test Categories

```python
# /a0/tests/test_obsidian.py

import pytest
import asyncio
from pathlib import Path

# === Unit Tests ===

class TestVaultManager:
    """Unit tests for VaultManager"""
    
    @pytest.mark.asyncio
    async def test_read_note(self, test_vault):
        manager = VaultManager(test_vault)
        note = await manager.read_note("test.md")
        assert note.content is not None
    
    @pytest.mark.asyncio
    async def test_write_note(self, test_vault):
        manager = VaultManager(test_vault)
        result = await manager.write_note(
            "new.md", 
            "# Test Content"
        )
        assert result.success
    
    @pytest.mark.asyncio
    async def test_parse_frontmatter(self, test_vault):
        manager = VaultManager(test_vault)
        note = await manager.read_note("with_frontmatter.md")
        assert note.frontmatter.get("title") == "Test"


class TestIndexEngine:
    """Unit tests for IndexEngine"""
    
    @pytest.mark.asyncio
    async def test_index_note(self, test_vault):
        engine = IndexEngine(test_vault)
        await engine.initialize()
        await engine.index_note("test.md")
        results = await engine.search("test")
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_backlinks(self, test_vault):
        engine = IndexEngine(test_vault)
        await engine.initialize()
        backlinks = await engine.get_backlinks("target.md")
        assert "source.md" in backlinks


class TestSwarmCoordinator:
    """Unit tests for SwarmCoordinator"""
    
    @pytest.mark.asyncio
    async def test_concurrent_search(self, test_vault):
        coordinator = SwarmCoordinator(test_vault)
        result = await coordinator.execute_search(
            query="test",
            pattern="concurrent",
            max_agents=3
        )
        assert result["success"]
    
    @pytest.mark.asyncio
    async def test_moa_analysis(self, test_vault):
        coordinator = SwarmCoordinator(test_vault)
        result = await coordinator.analyze_content(
            paths=["test1.md", "test2.md"],
            task="Summarize content",
            pattern="moa"
        )
        assert "analysis" in result


# === Integration Tests ===

class TestMCPServer:
    """Integration tests for MCP server"""
    
    @pytest.mark.asyncio
    async def test_tool_call(self, mcp_server):
        result = await mcp_server._handle_tool_call(
            "obsidian_read_note",
            {"path": "test.md"}
        )
        assert result[0].type == "text"


class TestObsidianTool:
    """Integration tests for ObsidianTool"""
    
    @pytest.mark.asyncio
    async def test_execute_search(self, tool):
        result = await tool.execute(
            operation="search",
            query="test"
        )
        assert result["success"]
    
    @pytest.mark.asyncio
    async def test_execute_swarm(self, tool):
        result = await tool.execute(
            operation="swarm",
            swarm_type="search",
            query="test",
            pattern="concurrent"
        )
        assert result["success"]


# === Performance Tests ===

class TestPerformance:
    """Performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_search_latency(self, large_vault):
        """Search should complete within 200ms"""
        engine = IndexEngine(large_vault)
        start = time.time()
        await engine.search("test")
        latency = time.time() - start
        assert latency < 0.2
    
    @pytest.mark.asyncio
    async def test_parallel_speedup(self, large_vault):
        """Parallel search should be faster"""
        coordinator = SwarmCoordinator(large_vault)
        
        # Sequential
        start = time.time()
        await coordinator._search_single("test")
        sequential_time = time.time() - start
        
        # Parallel
        start = time.time()
        await coordinator.execute_search("test", pattern="concurrent")
        parallel_time = time.time() - start
        
        assert parallel_time < sequential_time


# === Fixtures ===

@pytest.fixture
def test_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "test.md").write_text("# Test Note")
    yield vault

@pytest.fixture
def large_vault(tmp_path):
    vault = tmp_path / "large_vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    for i in range(10000):
        (vault / f"note_{i}.md").write_text(f"# Note {i}\n\nContent {i}")
    yield vault
```

### 9.2 Test Coverage Requirements

| Component | Target Coverage | Critical Paths |
|-----------|----------------|----------------|
| VaultManager | 95% | Read, write, parse |
| IndexEngine | 90% | Index, search, graph |
| SwarmCoordinator | 85% | All patterns |
| MCPServer | 90% | All tools |
| ObsidianTool | 95% | All operations |
| Security | 100% | Access control |

---

## 10. Deployment Guide

### 10.1 Installation

```bash
# 1. Set vault path
export OBSIDIAN_VAULT_PATH=/path/to/your/vault

# 2. Run setup script
python /a0/scripts/obsidian_setup.py

# 3. Verify installation
python -c "from python.tools.obsidian import ObsidianTool; print('OK')"
```

### 10.2 Setup Script

```python
# /a0/scripts/obsidian_setup.py

import os
import json
from pathlib import Path

def setup_obsidian():
    """Initialize Obsidian integration"""
    
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH not set")
    
    vault = Path(vault_path).expanduser()
    
    # Create .obsidian directory if needed
    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    
    # Create Agent Zero config
    config_path = obsidian_dir / "a0-config.json"
    default_config = {
        "version": "1.0.0",
        "indexing": {
            "auto_reindex": True,
            "reindex_interval": 3600
        },
        "search": {
            "default_mode": "fulltext",
            "default_limit": 50
        },
        "swarm": {
            "enabled": True,
            "max_agents": 10
        }
    }
    
    if not config_path.exists():
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)
    
    # Create templates directory
    templates_dir = vault / "Templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create default templates
    (templates_dir / "Daily Note.md").write_text("""---
date: {{ date }}
tags: [daily]
---

# {{ date }}

## Tasks
- [ ] 

## Notes

""")
    
    print(f"Obsidian integration initialized for: {vault}")
    print(f"Config: {config_path}")
    print("Ready to use!")


if __name__ == "__main__":
    setup_obsidian()
```

### 10.3 Health Check

```python
# /a0/scripts/obsidian_health.py

import asyncio
from python.tools.obsidian import ObsidianTool

async def health_check():
    """Verify Obsidian integration is working"""
    
    checks = []
    
    # Check 1: Tool initialization
    try:
        tool = ObsidianTool()
        checks.append(("Tool initialization", True, None))
    except Exception as e:
        checks.append(("Tool initialization", False, str(e)))
        return checks
    
    # Check 2: Vault access
    try:
        result = await tool.execute(operation="vault", vault_action="info")
        checks.append(("Vault access", result.get("success", False), None))
    except Exception as e:
        checks.append(("Vault access", False, str(e)))
    
    # Check 3: Search
    try:
        result = await tool.execute(operation="search", query="test", limit=1)
        checks.append(("Search", result.get("success", False), None))
    except Exception as e:
        checks.append(("Search", False, str(e)))
    
    # Check 4: Swarm
    try:
        result = await tool.execute(
            operation="swarm",
            swarm_type="search",
            query="test",
            pattern="concurrent",
            max_agents=2
        )
        checks.append(("Swarm", result.get("success", False), None))
    except Exception as e:
        checks.append(("Swarm", False, str(e)))
    
    return checks


if __name__ == "__main__":
    results = asyncio.run(health_check())
    
    print("\n=== Obsidian Health Check ===\n")
    
    all_passed = True
    for name, passed, error in results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
        if error:
            print(f"  Error: {error}")
        all_passed = all_passed and passed
    
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
```

---

## Summary

This specification defines a comprehensive native integration of Obsidian into Agent Zero with:

- **25+ MCP tools** for vault operations
- **7 swarm patterns** for parallel processing
- **Complete CRUD** operations for notes, metadata, templates
- **Advanced search** with full-text, semantic, and hybrid modes
- **Graph analysis** with clustering, centrality, and path finding
- **Enterprise-grade** security, audit logging, and performance optimization

**Total Implementation Time:** 19-24 days

**Key Deliverables:**
1. MCP Server with native tool access
2. Main Obsidian tool with swarm integration
3. Complete helper library (vault, index, cache, swarm)
4. Skill definition with procedures and templates
5. Comprehensive test suite (>90% coverage)
6. Documentation and deployment scripts

---

*End of Specification Document*
