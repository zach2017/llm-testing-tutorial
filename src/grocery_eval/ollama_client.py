"""Minimal, dependency-free client for the Ollama HTTP API (/api/chat, /api/tags, /api/version)."""

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class OllamaError(RuntimeError):
    """Raised for any transport or API failure. The message is stored in the result row."""


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", timeout: float = 180.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ transport
    def _request(self, path: str, payload: Optional[dict] = None) -> dict:
        url = self.host + path
        data = None
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            method = "POST"
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise OllamaError(f"HTTP {e.code} from {url}: {detail[:300]}") from e
        except urllib.error.URLError as e:
            raise OllamaError(f"Could not reach Ollama at {self.host}: {e.reason}") from e
        except (socket.timeout, TimeoutError) as e:
            raise OllamaError(f"Timed out after {self.timeout}s waiting for {url}") from e
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise OllamaError(f"Non-JSON response from {url}: {body[:300]}") from e

    # ------------------------------------------------------------------ helpers
    def version(self) -> Optional[str]:
        try:
            return self._request("/api/version").get("version")
        except OllamaError:
            return None

    def list_models(self) -> List[str]:
        data = self._request("/api/tags")
        return [m.get("name") or m.get("model") for m in data.get("models", [])]

    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.0,
             seed: Optional[int] = None, num_predict: int = 400, num_ctx: Optional[int] = None,
             think: Optional[bool] = None) -> Dict[str, Any]:
        """Non-streaming chat completion. Returns a normalised dict (see keys below)."""
        options: Dict[str, Any] = {"temperature": temperature, "num_predict": num_predict}
        if seed is not None:
            options["seed"] = seed
        if num_ctx:
            options["num_ctx"] = num_ctx
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False, "options": options}
        if think is not None:          # only sent when explicitly requested; not all models accept it
            payload["think"] = think

        t0 = time.perf_counter()
        data = self._request("/api/chat", payload)
        latency = time.perf_counter() - t0

        msg = data.get("message") or {}
        eval_count = data.get("eval_count") or 0
        eval_dur = (data.get("eval_duration") or 0) / 1e9
        return {
            "content": msg.get("content") or "",
            "thinking": msg.get("thinking") or "",
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": eval_count,
            "latency_s": latency,
            "generation_s": eval_dur,
            "load_s": (data.get("load_duration") or 0) / 1e9,
            "tokens_per_s": (eval_count / eval_dur) if eval_dur > 0 else None,
            "done_reason": data.get("done_reason"),
        }
