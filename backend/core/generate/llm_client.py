import logging
from typing import Generator, List, Dict, Optional, Union
from groq import Groq
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Groq Chat Completion Client.
    Maintains same API contract as previous HF version.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.config = settings.llm

    def generate(
        self,
        messages: List[Dict[str, str]],
        stream: Optional[bool] = None
    ) -> Union[Generator[str, None, None], str]:

        use_stream = stream if stream is not None else self.config.stream
        model = self.config.model

        try:
            if use_stream:
                return self._stream_response(model, messages)
            else:
                return self._sync_response(model, messages)

        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise

    def _sync_response(self, model: str, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.config.temperature,
            max_completion_tokens=self.config.max_tokens,
            stream=False
        )

        return response.choices[0].message.content

    def _stream_response(
        self,
        model: str,
        messages: List[Dict[str, str]]
    ) -> Generator[str, None, None]:

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.config.temperature,
            max_completion_tokens=self.config.max_tokens,
            stream=True
        )

        yielded_any = False

        for chunk in stream:
            if not chunk.choices:
                logger.debug("Chunk received with empty choices")
                continue

            delta = chunk.choices[0].delta
            if not delta:
                logger.debug("Chunk received with empty delta")
                continue

            content = getattr(delta, "content", None)
            finish_reason = getattr(chunk.choices[0], "finish_reason", None)

            if finish_reason:
                logger.debug(f"Chunk received with finish_reason: {finish_reason}")

            if content:
                yielded_any = True
                logger.debug(f"Streaming chunk: {repr(content[:50])}")
                yield content
            else:
                logger.debug("Chunk received with None content")

        # Prevent empty-stream termination
        if not yielded_any:
            logger.warning("No chunks yielded from Groq stream")
            yield "not found in document"
        else:
            logger.debug("Stream completed successfully")
