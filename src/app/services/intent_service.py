from typing import Dict
import logging
from openai import AsyncOpenAI
from src.app.integrations.redis import RedisService
from fastapi import HTTPException

logger = logging.getLogger(__name__)


INTENT_PROMPTS: Dict[str, str] = {
    "diet": "You are a nutrition expert. Provide personalized diet recommendations.",
    "fitness": "You are a fitness coach. Provide workout plans and advice.",
    "medical": "You are a medical professional. Answer health-related inquiries carefully.",
}


class IntentService:
    def __init__(self, llm_client: AsyncOpenAI, redis_service: RedisService):
        self._llm_client = llm_client
        self._redis = redis_service

    async def classify_intent(self, user_id: str, text: str) -> str:
        # Здесь простой вызов LLM для классификации intent
        prompt = (
            "Классифицируй запрос по категориям: diet, fitness, medical. "
            f"Если ни одна не подходит, возвращай unknown.\n"
            f"Запрос: {text}\n"
            "Категория:"
        )
        try:
            resp = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты классификатор intent."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=10,
                temperature=0,
            )
            intent = resp.choices[0].message.content.strip().lower()
            if intent not in INTENT_PROMPTS:
                intent = "unknown"

            # сохраняем intent в redis
            key = f"tg_user:{user_id}:intent"
            await self._redis.set(key, intent)
            logger.info(f"Intent for user {user_id} classified as: {intent}")
            return intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            raise HTTPException(
                status_code=500, detail="Intent classification error"
            )

    def get_system_prompt(self, intent: str) -> str:
        return INTENT_PROMPTS.get(intent, "You are a general assistant.")

    async def rephrase_query(self, user_id: str, text: str) -> str:
        """
        Rephrase user's query to make it more specific and relevant for the RAG system.
        This is the REPHRASE step from the diagram.
        """
        try:
            # Получаем текущий intent пользователя
            intent_key = f"tg_user:{user_id}:intent"
            intent = await self._redis.get(intent_key) or "unknown"

            # Формируем промпт для перефразирования запроса
            system_prompt = (
                f"You are an AI assistant that helps to rephrase user queries to make them "
                f"more specific and relevant for the {intent} domain. "
                f"Keep the rephrased query concise but detailed."
            )

            user_prompt = (
                f"Original query: {text}\nRephrase this for {intent} domain:"
            )

            resp = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=150,
                temperature=0.7,
            )

            rephrased_query = resp.choices[0].message.content.strip()
            logger.info(
                f"Rephrased query for user {user_id}: {rephrased_query}"
            )

            # Сохраняем перефразированный запрос в Redis для дальнейшего использования
            await self._redis.set(
                f"tg_user:{user_id}:rephrased_query", rephrased_query, ex=3600
            )

            return rephrased_query

        except Exception as e:
            logger.error(f"Failed to rephrase query: {e}")
            # В случае ошибки возвращаем оригинальный запрос
            return text
