import json
import logging
import httpx
import time
import random
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
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "HTTP-Referer": "https://docsense-rag.internal",
            "X-Title": "DocSense RAG",
            "Content-Type": "application/json"
        }
        self.max_retries = 3
        self.base_delay = 2.0

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

        if not use_stream:
            try:
                return self._call_api(payload, use_stream)
            except Exception as e:
                logger.warning(f"Primary model {payload['model']} failed: {e}. Trying fallback.")
                if self.config.fallback_model:
                    payload["model"] = self.config.fallback_model
                    return self._call_api(payload, use_stream)
                raise e
        else:
            return self._stream_with_fallback(payload)

    def _stream_with_fallback(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """Wrapper to handle model fallback during streaming."""
        original_model = payload["model"]
        try:
            # We must iterate at least once or check status to trigger the exception
            # if the initial connection fails (like a 400).
            gen = self._stream_response(payload)
            for chunk in gen:
                yield chunk
        except Exception as e:
            # Only fallback if we have a fallback model defined.
            if self.config.fallback_model and original_model != self.config.fallback_model:
                logger.warning(f"Streaming failed for {original_model}: {e}. Trying fallback.")
                payload["model"] = self.config.fallback_model
                yield from self._stream_response(payload)
            else:
                raise e

    def _call_api(self, payload: Dict[str, Any], stream: bool) -> Union[Generator[str, None, None], str]:
        if stream:
            return self._stream_response(payload)
        else:
            return self._sync_response(payload)

    def _sync_response(self, payload: Dict[str, Any]) -> str:
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(self.base_url, headers=self.headers, json=payload)
                    
                    if response.status_code == 429:
                        delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Rate limited (429). Retrying in {delay:.2f}s... (Attempt {attempt+1}/{self.max_retries})")
                        time.sleep(delay)
                        continue
                        
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Request failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
        
        raise Exception("Failed after maximum retries")

    def _stream_response(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=60.0) as client:
                    with client.stream("POST", self.base_url, headers=self.headers, json=payload) as response:
                        if response.status_code == 429:
                            delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"Rate limited (429) during stream initiation. Retrying in {delay:.2f}s...")
                            time.sleep(delay)
                            continue

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
                        return # Successfully finished stream
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Stream failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
