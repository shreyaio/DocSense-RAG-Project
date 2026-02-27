import json
import logging
import httpx
from typing import Generator, List, Dict, Any, Optional, Union
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """
    OpenRouter API Client for document-grounded generation.
    Supports streaming and model fallback.
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.config = settings.llm
        self.base_url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://docsense-rag.internal",
            "X-Title": "DocSense RAG",
            "Content-Type": "application/json"
        }

    def generate(self, messages: List[Dict[str, str]], stream: Optional[bool] = None) -> Union[Generator[str, None, None], str]:
        """
        Calls OpenRouter API to generate a response.
        If stream=True, returns a generator of tokens (strings).
        If stream=False, returns the full response string.
        """
        use_stream = stream if stream is not None else self.config.stream
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": use_stream
        }

        if not self.api_key or self.api_key == "":
             logger.warning("OPENROUTER_API_KEY is not set. LLM calls will fail.")

        try:
            return self._call_api(payload, use_stream)
        except Exception as e:
            logger.warning(f"Primary model {self.config.model} failed: {e}. Trying fallback.")
            if self.config.fallback_model:
                payload["model"] = self.config.fallback_model
                return self._call_api(payload, use_stream)
            raise e

    def _call_api(self, payload: Dict[str, Any], stream: bool) -> Union[Generator[str, None, None], str]:
        if stream:
            return self._stream_response(payload)
        else:
            return self._sync_response(payload)

    def _sync_response(self, payload: Dict[str, Any]) -> str:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _stream_response(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", self.base_url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    if line.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(line)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
