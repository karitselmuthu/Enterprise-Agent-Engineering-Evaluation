"""Optional Ollama backend using its native /api/chat tool calling API."""
import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from src.tools.executor import ToolResult


class OllamaBackend:
    def __init__(self, model: str, url: str = "http://127.0.0.1:11434/api/chat",
                 post: Callable[[dict], dict] | None = None):
        if not model:
            raise ValueError("model is required")
        self.model, self.url = model, url
        self.post = post or self._post
        self._assistant_message: dict[str, Any] | None = None

    def _post(self, payload: dict) -> dict:
        request = Request(self.url, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def _chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False}
        if tools is not None:
            payload["tools"] = tools
        message = self.post(payload).get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama returned no message")
        return message

    def select_tool(self, request: str, tools: list[dict[str, Any]]
                    ) -> tuple[str, dict[str, Any]] | None:
        definitions = [{"type": "function", "function": {
            "name": t["name"], "description": t["description"],
            "parameters": t["inputSchema"]}} for t in tools]
        message = self._chat([{"role": "user", "content": request}], definitions)
        self._assistant_message = message
        calls = message.get("tool_calls") or []
        if not calls:
            return None
        function = calls[0].get("function", {})
        arguments = function.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("Model returned non-object tool arguments")
        return function.get("name", ""), arguments

    def interpret(self, request: str, result: ToolResult) -> str:
        tool_data = result.content if result.ok else {"error": result.error,
                                                       "error_code": result.error_code}
        messages = [{"role": "user", "content": request}]
        if self._assistant_message:
            messages.append(self._assistant_message)
        messages.append({"role": "tool", "tool_name": result.name,
                         "content": json.dumps(tool_data)})
        return str(self._chat(messages).get("content", "")).strip()
