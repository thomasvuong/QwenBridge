"""
tool_agent.py — General-purpose tool execution agent.

Executes: web search, code execution, file read/write, HTTP requests.
Uses qwen-coder-plus for code tasks, qwen-turbo for lightweight operations.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

import config
from router import model_router

console = Console()

SYSTEM_PROMPT = """You are QwenBridge Tool Agent.

Given a task, produce a JSON action plan:
{
  "action": "search|code|read_file|http_get|shell",
  "query":  "...",   // for search
  "code":   "...",   // for code execution (Python)
  "url":    "...",   // for http_get
  "path":   "...",   // for file ops
  "command": "..."   // for shell (if allowed)
}

Be precise. Only request tools that are needed."""


class ToolAgent:
    def __init__(self):
        # OSS client for file storage
        self._oss = None
        self._init_oss()

    def _init_oss(self):
        if config.MOCK_MODE:
            console.print("[dim magenta]🔷 MOCK ToolAgent: OSS disabled[/dim magenta]")
            return
        try:
            import oss2
            auth = oss2.Auth(config.ALI_ACCESS_KEY_ID, config.ALI_ACCESS_KEY_SECRET)
            self._oss = oss2.Bucket(auth, config.OSS_ENDPOINT, config.OSS_BUCKET)
            console.print("[green]✓ ToolAgent: OSS connected[/green]")
        except Exception as e:
            console.print(f"[yellow]ToolAgent: OSS unavailable ({e})[/yellow]")

    async def execute(self, task: str, session_id: str = "default") -> dict[str, Any]:
        console.print(f"[green]ToolAgent:[/green] {task[:80]}")
        # Decide action via LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": task},
        ]
        text, _ = model_router.call(
            messages,
            task={"requires_code": True, "complexity": "simple"},
            response_format={"type": "json_object"},
        )
        try:
            plan = json.loads(text)
        except json.JSONDecodeError:
            return {"error": "Could not parse tool plan", "raw": text[:200]}

        action = plan.get("action", "")
        return await self._dispatch(action, plan, task)

    async def _dispatch(self, action: str, plan: dict, original: str) -> dict:
        if action == "search":
            return await self._search(plan.get("query", original))
        if action == "code":
            return self._run_code(plan.get("code", ""))
        if action == "http_get":
            return await self._http_get(plan.get("url", ""))
        if action == "read_file":
            return self._read_file(plan.get("path", ""))
        if action == "shell":
            return self._shell(plan.get("command", ""))
        # Fallback: just answer via LLM
        return await self._llm_answer(original)

    async def _search(self, query: str) -> dict:
        """Use Qwen to answer as if searching — real web search in prod via tool_calls."""
        messages = [
            {"role": "system", "content": "Answer this search query concisely using your knowledge. Include sources if known."},
            {"role": "user",   "content": query},
        ]
        text, _ = model_router.call(messages, task={"complexity": "simple"})
        return {"action": "search", "query": query, "result": text}

    def _run_code(self, code: str) -> dict:
        """Execute Python code in a subprocess (sandboxed temp dir)."""
        if not code:
            return {"error": "No code provided"}
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "script.py"
            src.write_text(code)
            try:
                result = subprocess.run(
                    ["python3", str(src)],
                    capture_output=True, text=True, timeout=30, cwd=tmpdir
                )
                return {
                    "action": "code",
                    "code":   code[:200],
                    "stdout": result.stdout[:1000],
                    "stderr": result.stderr[:500],
                    "exit_code": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"error": "Code execution timed out (30s)"}
            except Exception as e:
                return {"error": str(e)}

    async def _http_get(self, url: str) -> dict:
        if not url:
            return {"error": "No URL provided"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, follow_redirects=True)
                return {
                    "action":      "http_get",
                    "url":         url,
                    "status":      resp.status_code,
                    "content":     resp.text[:2000],
                }
        except Exception as e:
            return {"error": str(e), "url": url}

    def _read_file(self, path: str) -> dict:
        try:
            content = Path(path).read_text(errors="replace")
            return {"action": "read_file", "path": path, "content": content[:3000]}
        except Exception as e:
            return {"error": str(e), "path": path}

    def _shell(self, command: str) -> dict:
        BLOCKLIST = ["rm -rf", "sudo", "chmod 777", "curl | sh", "wget | sh"]
        for blocked in BLOCKLIST:
            if blocked in command:
                return {"error": f"Blocked dangerous command: {blocked}"}
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=20
            )
            return {
                "action":    "shell",
                "command":   command,
                "stdout":    result.stdout[:1000],
                "stderr":    result.stderr[:300],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Shell command timed out"}

    async def _llm_answer(self, task: str) -> dict:
        messages = [
            {"role": "system", "content": "Answer this task directly and concisely."},
            {"role": "user",   "content": task},
        ]
        text, _ = model_router.call(messages, task={"complexity": "simple"})
        return {"action": "llm_answer", "result": text}

    # ── OSS file storage ──────────────────────────────────────────────────────

    def upload_file(self, local_path: str, oss_key: str) -> str | None:
        """Upload a file to Alibaba OSS. Returns public URL or None."""
        if not self._oss:
            return None
        try:
            self._oss.put_object_from_file(oss_key, local_path)
            return f"https://{config.OSS_BUCKET}.{config.OSS_ENDPOINT.lstrip('https://')}/{oss_key}"
        except Exception as e:
            console.print(f"[red]OSS upload failed: {e}[/red]")
            return None
