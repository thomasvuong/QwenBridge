"""
memory_agent.py — Persistent cross-session memory via Alibaba Cloud Table Store.

Stores and retrieves agent context, facts, and session history.
Falls back to a local JSON file when Table Store is unavailable (dev mode).
"""
from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Any

from rich.console import Console

import config

console = Console()
_LOCAL_STORE = Path("/tmp/qwenbridge_memory.json")


class MemoryAgent:
    def __init__(self):
        self._ts_client = None
        self._use_local = False
        self._init_tablestore()

    def _init_tablestore(self):
        if config.MOCK_MODE:
            self._use_local = True
            console.print("[dim magenta]🔷 MOCK MemoryAgent: using local JSON store[/dim magenta]")
            return
        try:
            import tablestore as ts
            self._ts_client = ts.OTSClient(
                config.TABLESTORE_ENDPOINT,
                config.ALI_ACCESS_KEY_ID,
                config.ALI_ACCESS_KEY_SECRET,
                config.TABLESTORE_INSTANCE,
            )
            self._ensure_table()
            console.print("[green]✓ MemoryAgent: Table Store connected[/green]")
        except Exception as e:
            console.print(f"[yellow]MemoryAgent: Table Store unavailable ({e}), using local fallback[/yellow]")
            self._use_local = True

    def _ensure_table(self):
        """Create memory table if it doesn't exist."""
        import tablestore as ts
        try:
            self._ts_client.describe_table("agent_memory")
        except Exception:
            schema = ts.TableMeta(
                "agent_memory",
                [("session_id", "STRING"), ("timestamp", "INTEGER")],
            )
            capacity = ts.ReservedThroughput(ts.CapacityUnit(0, 0))
            options  = ts.TableOptions(time_to_live=-1, max_version=1)
            self._ts_client.create_table(schema, capacity, options)
            console.print("[green]✓ Created Table Store table: agent_memory[/green]")

    # ── Public API ────────────────────────────────────────────────────────────

    async def store(self, session_id: str, data: dict[str, Any]) -> str:
        """Persist a memory entry. Returns the entry key."""
        ts_now  = int(time.time() * 1000)
        content = json.dumps(data, ensure_ascii=False)
        key     = hashlib.md5(f"{session_id}{ts_now}".encode()).hexdigest()[:8]

        if self._use_local:
            store = self._load_local()
            store.setdefault(session_id, []).append({
                "key": key, "ts": ts_now, "data": data
            })
            self._save_local(store)
        else:
            self._ts_put(session_id, ts_now, content, key)

        console.print(f"[dim]MemoryAgent: stored [{key}] for session {session_id[:8]}[/dim]")
        return key

    async def recall(self, session_id: str, limit: int = 10) -> list[str]:
        """Retrieve recent memories as human-readable strings."""
        if self._use_local:
            store = self._load_local()
            entries = store.get(session_id, [])[-limit:]
        else:
            entries = self._ts_query(session_id, limit)

        results = []
        for entry in entries:
            data = entry.get("data", entry)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            results.append(self._format(data))
        return results

    async def execute(self, task: str, session_id: str = "default") -> dict:
        """Execute a memory operation described in natural language."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["store", "remember", "save", "record"]):
            key = await self.store(session_id, {"raw_task": task})
            return {"action": "stored", "key": key}
        elif any(w in task_lower for w in ["recall", "retrieve", "find", "get", "what"]):
            memories = await self.recall(session_id, limit=5)
            return {"action": "recalled", "memories": memories}
        else:
            memories = await self.recall(session_id, limit=3)
            return {"action": "context", "recent_memories": memories}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _ts_put(self, session_id: str, ts_ms: int, content: str, key: str):
        import tablestore as ts
        pks = [("session_id", session_id), ("timestamp", ts_ms)]
        attrs = [("content", content), ("entry_key", key)]
        cond = ts.Condition(ts.RowExistenceExpectation.IGNORE)
        self._ts_client.put_row("agent_memory", ts.Row(pks, attrs), cond)

    def _ts_query(self, session_id: str, limit: int) -> list[dict]:
        import tablestore as ts
        start = [("session_id", session_id), ("timestamp", ts.INF_MIN)]
        end   = [("session_id", session_id), ("timestamp", ts.INF_MAX)]
        criteria = ts.RangeRowQueryCriteria(
            "agent_memory", start, end,
            max_version=1, limit=limit,
            direction=ts.Direction.BACKWARD,
        )
        _, rows, _ = self._ts_client.get_range(
            "agent_memory", criteria, ts.Direction.BACKWARD
        )
        result = []
        for row in rows:
            data = {}
            for attr in row.attribute_columns:
                data[attr[0]] = attr[1]
            result.append({"data": data.get("content", ""), "key": data.get("entry_key", "")})
        return result

    def _load_local(self) -> dict:
        if _LOCAL_STORE.exists():
            try:
                return json.loads(_LOCAL_STORE.read_text())
            except Exception:
                pass
        return {}

    def _save_local(self, store: dict):
        _LOCAL_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2))

    @staticmethod
    def _format(data: Any) -> str:
        if isinstance(data, dict):
            return " | ".join(f"{k}: {str(v)[:50]}" for k, v in data.items())
        return str(data)[:200]
