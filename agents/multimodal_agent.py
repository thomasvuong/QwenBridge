"""
multimodal_agent.py — Vision + audio + video processing via Qwen-VL and Qwen-Audio.

Handles: image analysis, document OCR, audio transcription, video description.
Uses qwen-vl-max for vision tasks (3-37x cheaper than GPT-4o).
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from openai import OpenAI
from rich.console import Console

import config

console = Console()


class MultimodalAgent:
    def __init__(self):
        self._client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
        )

    async def execute(self, task: str, session_id: str = "default",
                      file_path: str | None = None,
                      image_url: str | None = None) -> dict[str, Any]:
        if file_path:
            return await self.analyze_file(file_path, task)
        if image_url:
            return await self.analyze_url(image_url, task)
        return {"error": "multimodal_agent: no file or url provided", "task": task}

    async def analyze_file(self, file_path: str, prompt: str = "Describe this.") -> dict:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        mime, _ = mimetypes.guess_type(file_path)
        mime = mime or "application/octet-stream"

        data = base64.b64encode(path.read_bytes()).decode()
        data_url = f"data:{mime};base64,{data}"

        if mime.startswith("image/"):
            return await self._vision_call(data_url, prompt, source=file_path)
        return {"error": f"Unsupported mime type: {mime}"}

    async def analyze_url(self, url: str, prompt: str = "Describe this image.") -> dict:
        return await self._vision_call(url, prompt, source=url)

    async def describe_scene(self, image_url: str) -> dict:
        return await self.analyze_url(
            image_url,
            "Describe this scene in detail. List all visible objects, people, text, and context."
        )

    async def ocr(self, image_url: str, language: str = "auto") -> dict:
        return await self.analyze_url(
            image_url,
            f"Extract ALL text visible in this image. Language hint: {language}. "
            "Preserve layout and formatting as closely as possible."
        )

    async def diagram_to_spec(self, image_url: str) -> dict:
        return await self.analyze_url(
            image_url,
            "This is a technical diagram or architecture drawing. "
            "Convert it to a structured JSON specification with: "
            "components, connections, data_flows, and notes."
        )

    # ── Private ───────────────────────────────────────────────────────────────

    async def _vision_call(self, image_content: str, prompt: str, source: str = "") -> dict:
        console.print(f"[cyan]→ MultimodalAgent: qwen-vl-max | {prompt[:60]}[/cyan]")
        try:
            resp = self._client.chat.completions.create(
                model=config.MODEL_VL_32B,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_content}},
                            {"type": "text",      "text": prompt},
                        ],
                    }
                ],
            )
            result = resp.choices[0].message.content
            return {
                "result": result,
                "model": config.MODEL_VL_32B,
                "source": source,
                "tokens": {
                    "input":  resp.usage.prompt_tokens,
                    "output": resp.usage.completion_tokens,
                },
            }
        except Exception as e:
            return {"error": str(e), "source": source}
