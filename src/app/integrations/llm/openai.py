import logging
from typing import List, Dict
from openai import AsyncOpenAI
from fastapi import HTTPException

from .base import LLMService


logger = logging.getLogger(__name__)


class OpenaiService(LLMService):
    def __init__(self, llm_client: AsyncOpenAI, model: str) -> None:
        self._llm_client = llm_client
        self._model = model

    async def get_response(
        self, prompt_query: str, system_prompt: str
    ) -> Dict[str, List[Dict]]:

        messages = []

        system_message = {"role": "system", "content": system_prompt}
        text_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_query},
            ],
        }

        messages.append(system_message)
        messages.append(text_message)
        logger.debug(f"Sending OpenAI request: {messages}")
        try:
            completion = await self._llm_client.chat.completions.create(
                model=self._model,
                messages=messages,
                top_p=1.0,
                max_completion_tokens=2500,
                timeout=60,
            )

            response = completion.choices[0].message.content
            logger.debug(f"OpenAI response: {response}")

            return response

        except Exception as e:
            logger.error(f"YandexGPT request failed: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Error with openai response: {e}"
            )
