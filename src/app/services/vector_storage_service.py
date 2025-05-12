import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class VectorStorageService:
    """
    Service for managing vector storage operations
    """

    def __init__(self, weaviate_client):
        """
        Initialize the vector storage service with a ready-to-use Weaviate client

        Args:
            weaviate_client: Initialized Weaviate client
        """
        self._client = weaviate_client

    async def store_user_query(
        self, user_id: str, query: str, embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        """
        Store a user query with its embedding

        Args:
            user_id: Telegram user ID
            query: The user's query text
            embedding: Optional pre-computed embedding vector

        Returns:
            UUID of the created object or None if failed
        """
        try:
            # Make sure the class exists
            await self._ensure_queries_class_exists()

            # Create the object
            properties = {
                "user_id": user_id,
                "query_text": query,
                "timestamp": self._get_current_timestamp(),
            }

            # Если предоставлен embedding, используем его, иначе Weaviate сам сгенерирует
            if embedding:
                return self._client.add_object(
                    class_name="UserQuery",
                    properties=properties,
                    vector=embedding,
                )
            else:
                return self._client.add_object(
                    class_name="UserQuery",
                    properties=properties,
                    # vector не указываем, чтобы Weaviate использовал text2vec-openai
                )
        except Exception as e:
            logger.error(f"Error storing user query: {e}")
            return None

    async def find_similar_queries(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar queries to the given query

        Args:
            query: Query text to find similar queries for
            limit: Maximum number of results to return

        Returns:
            List of similar queries
        """
        try:
            # Используем text2vec-openai для поиска по тексту
            return self._client.search_objects(
                class_name="UserQuery",
                query_text=query,  # text2vec-openai автоматически создаст вектор для поиска
                properties=["user_id", "query_text", "timestamp"],
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error finding similar queries: {e}")
            return []

    async def store_message_history(
        self,
        user_id: str,
        query: str,
        response: str,
        intent: str,
        embedding: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Store a message exchange with its embedding

        Args:
            user_id: Telegram user ID
            query: The user's query text
            response: The bot's response
            intent: The detected intent
            embedding: Optional pre-computed embedding vector

        Returns:
            UUID of the created object or None if failed
        """
        try:
            # Make sure the class exists
            await self._ensure_message_history_class_exists()

            # Create the object
            properties = {
                "user_id": user_id,
                "query": query,
                "response": response,
                "intent": intent,
                "timestamp": self._get_current_timestamp(),
            }

            # Если предоставлен embedding, используем его, иначе Weaviate сам сгенерирует
            if embedding:
                return self._client.add_object(
                    class_name="MessageHistory",
                    properties=properties,
                    vector=embedding,
                )
            else:
                return self._client.add_object(
                    class_name="MessageHistory",
                    properties=properties,
                    # vector не указываем, чтобы Weaviate использовал text2vec-openai
                )
        except Exception as e:
            logger.error(f"Error storing message history: {e}")
            return None

    async def get_user_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get message history for a specific user

        Args:
            user_id: Telegram user ID
            limit: Maximum number of results to return

        Returns:
            List of message history objects
        """
        try:
            # Получаем коллекцию MessageHistory
            collection = self._client.client.collections.get("MessageHistory")

            # Настраиваем фильтр по user_id
            filter_by = {
                "path": ["user_id"],
                "operator": "Equal",
                "valueString": user_id,
            }

            # Выполняем запрос с фильтром
            result = (
                collection.query.with_where(filter_by)
                .with_limit(limit)
                .with_fields(["query", "response", "intent", "timestamp"])
                .do()
            )

            return result.objects
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return []

    async def _ensure_queries_class_exists(self) -> None:
        """
        Make sure the UserQuery class exists in the schema
        """
        try:
            # Проверяем, существует ли коллекция
            try:
                self._client.client.collections.get("UserQuery")
                # Если коллекция существует, ничего не делаем
                return
            except Exception:
                # Коллекция не существует, создаем ее
                pass

            # Создаем схему для коллекции UserQuery
            class_obj = {
                "class": "UserQuery",
                "description": "User queries to the bot",
                "vectorizer": "text2vec-openai",  # Используем OpenAI для автоматической векторизации
                "moduleConfig": {
                    "text2vec-openai": {
                        "model": "text-embedding-ada-002",
                        "type": "text",
                    }
                },
                "properties": [
                    {
                        "name": "user_id",
                        "dataType": ["string"],
                        "description": "Telegram user ID",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True  # Пропускаем ID при векторизации
                            }
                        },
                    },
                    {
                        "name": "query_text",
                        "dataType": ["text"],
                        "description": "The query text from the user",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,  # Не пропускать это поле при векторизации
                                "vectorizePropertyName": False,  # Не включать имя поля в векторизацию
                            }
                        },
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["string"],
                        "description": "When the query was made",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True  # Пропускаем timestamp при векторизации
                            }
                        },
                    },
                ],
            }
            self._client.create_class(class_obj)
        except Exception as e:
            logger.error(f"Error creating UserQuery class: {e}")
            # Продолжаем работу даже при ошибке

    async def _ensure_message_history_class_exists(self) -> None:
        """
        Make sure the MessageHistory class exists in the schema
        """
        try:
            # Проверяем, существует ли коллекция
            try:
                self._client.client.collections.get("MessageHistory")
                # Если коллекция существует, ничего не делаем
                return
            except Exception:
                # Коллекция не существует, создаем ее
                pass

            # Создаем схему для коллекции MessageHistory
            class_obj = {
                "class": "MessageHistory",
                "description": "Message history between users and the bot",
                "vectorizer": "text2vec-openai",  # Используем OpenAI для автоматической векторизации
                "moduleConfig": {
                    "text2vec-openai": {
                        "model": "text-embedding-ada-002",
                        "type": "text",
                    }
                },
                "properties": [
                    {
                        "name": "user_id",
                        "dataType": ["string"],
                        "description": "Telegram user ID",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True  # Пропускаем ID при векторизации
                            }
                        },
                    },
                    {
                        "name": "query",
                        "dataType": ["text"],
                        "description": "The query from the user",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,  # Не пропускать это поле при векторизации
                            }
                        },
                    },
                    {
                        "name": "response",
                        "dataType": ["text"],
                        "description": "The response from the bot",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,  # Не пропускать это поле при векторизации
                            }
                        },
                    },
                    {
                        "name": "intent",
                        "dataType": ["string"],
                        "description": "The detected intent",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True  # Пропускаем intent при векторизации
                            }
                        },
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["string"],
                        "description": "When the exchange occurred",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True  # Пропускаем timestamp при векторизации
                            }
                        },
                    },
                ],
            }
            self._client.create_class(class_obj)
        except Exception as e:
            logger.error(f"Error creating MessageHistory class: {e}")
            # Продолжаем работу даже при ошибке

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.now().isoformat()
