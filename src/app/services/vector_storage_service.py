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
            # Убедимся, что класс существует
            await self._ensure_queries_class_exists()

            # Получаем коллекцию
            collection = self._client.client.collections.get("UserQuery")

            # Создаем объект с нужными свойствами
            properties = {
                "user_id": user_id,
                "query_text": query,
                "timestamp": self._get_current_timestamp(),
            }

            # Добавляем объект в коллекцию с вектором или без
            if embedding:
                result = collection.data.insert(
                    properties=properties, vector=embedding
                )
            else:
                # Vectorizer настроен в коллекции, так что вектор будет создан автоматически
                result = collection.data.insert(properties=properties)

            logger.info(
                f"Stored user query from user_id {user_id}: {query[:30]}..."
            )
            return result
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
            # В v4 API используем прямое обращение к коллекции и near_text
            try:
                collection = self._client.client.collections.get("UserQuery")
            except Exception as e:
                logger.error(f"Collection UserQuery not found: {e}")
                # Создаем коллекцию, если она не существует
                await self._ensure_queries_class_exists()
                collection = self._client.client.collections.get("UserQuery")

            # Используем near_text для поиска семантически похожих запросов
            result = (
                collection.query.near_text(query=query, limit=limit)
                .with_fields(["user_id", "query_text", "timestamp"])
                .do()
            )

            # Форматируем результаты в нужный формат
            similar_queries = []
            if hasattr(result, "objects") and result.objects:
                for obj in result.objects:
                    similar_queries.append(
                        {
                            "user_id": obj.properties.get("user_id", ""),
                            "query_text": obj.properties.get("query_text", ""),
                            "timestamp": obj.properties.get("timestamp", ""),
                        }
                    )

            return similar_queries
        except Exception as e:
            logger.error(f"Error finding similar queries: {e}")
            return []

    # Методы для работы с генетическими отчетами пользователей
    async def store_genetic_report(
        self,
        user_id: str,
        codelab: str,
        report_data: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Store a user's genetic report with vectorization

        Args:
            user_id: Telegram user ID
            codelab: User's lab code
            report_data: Report data from MyGenetics
            embedding: Optional pre-computed embedding vector

        Returns:
            UUID of the created object or None if failed
        """
        try:
            # Убедимся, что класс существует
            await self._ensure_genetic_reports_class_exists()

            # Получаем коллекцию
            collection = self._client.client.collections.get("GeneticReport")

            # Преобразуем report_data в текстовое представление для векторизации
            report_text = self._format_report_as_text(report_data)

            # Создаем объект с нужными свойствами
            properties = {
                "user_id": user_id,
                "codelab": codelab,
                "report_data": report_data,
                "report_text": report_text,
                "timestamp": self._get_current_timestamp(),
            }

            # Добавляем объект в коллекцию с вектором или без
            if embedding:
                result = collection.data.insert(
                    properties=properties, vector=embedding
                )
            else:
                # Vectorizer настроен в коллекции, так что вектор будет создан автоматически
                result = collection.data.insert(properties=properties)

            logger.info(
                f"Stored genetic report for user_id {user_id}, codelab: {codelab}"
            )
            return result
        except Exception as e:
            logger.error(f"Error storing genetic report: {e}")
            return None

    async def get_genetic_report(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get genetic report for a user

        Args:
            user_id: Telegram user ID

        Returns:
            Genetic report data or None if not found
        """
        try:
            try:
                collection = self._client.client.collections.get(
                    "GeneticReport"
                )
            except Exception as e:
                logger.error(f"Collection GeneticReport not found: {e}")
                return None

            # Set up filter by user_id
            filter_by = {
                "path": ["user_id"],
                "operator": "Equal",
                "valueString": user_id,
            }

            # Execute the query with filter
            result = (
                collection.query.with_where(filter_by)
                .with_limit(1)
                .with_fields(["codelab", "report_data", "timestamp"])
                .do()
            )

            # Return the first report if any
            if (
                hasattr(result, "objects")
                and result.objects
                and len(result.objects) > 0
            ):
                report = result.objects[0]
                return {
                    "codelab": report.properties.get("codelab", ""),
                    "report_data": report.properties.get("report_data", {}),
                    "timestamp": report.properties.get("timestamp", ""),
                }

            return None
        except Exception as e:
            logger.error(f"Error getting genetic report: {e}")
            return None

    # Методы для работы с базой знаний (методические данные)
    async def store_knowledge_article(
        self,
        title: str,
        content: str,
        category: str,
        tags: List[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Store a knowledge base article with vectorization

        Args:
            title: Article title
            content: Article content
            category: Article category
            tags: List of tags
            embedding: Optional pre-computed embedding vector

        Returns:
            UUID of the created object or None if failed
        """
        try:
            # Убедимся, что класс существует
            await self._ensure_knowledge_base_class_exists()

            # Получаем коллекцию
            collection = self._client.client.collections.get("KnowledgeBase")

            # Создаем объект с нужными свойствами
            properties = {
                "title": title,
                "content": content,
                "category": category,
                "tags": tags or [],
                "timestamp": self._get_current_timestamp(),
            }

            # Добавляем объект в коллекцию с вектором или без
            if embedding:
                result = collection.data.insert(
                    properties=properties, vector=embedding
                )
            else:
                # Vectorizer настроен в коллекции, так что вектор будет создан автоматически
                result = collection.data.insert(properties=properties)

            logger.info(f"Stored knowledge article: {title}")
            return result
        except Exception as e:
            logger.error(f"Error storing knowledge article: {e}")
            return None

    async def find_knowledge_articles(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find knowledge articles related to the query

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of related knowledge articles
        """
        try:
            try:
                collection = self._client.client.collections.get(
                    "KnowledgeBase"
                )
            except Exception as e:
                logger.error(f"Collection KnowledgeBase not found: {e}")
                await self._ensure_knowledge_base_class_exists()
                collection = self._client.client.collections.get(
                    "KnowledgeBase"
                )

            # Используем near_text для поиска семантически похожих статей
            result = (
                collection.query.near_text(query=query, limit=limit)
                .with_fields(
                    ["title", "content", "category", "tags", "timestamp"]
                )
                .do()
            )

            # Форматируем результаты в нужный формат
            articles = []
            if hasattr(result, "objects") and result.objects:
                for obj in result.objects:
                    articles.append(
                        {
                            "title": obj.properties.get("title", ""),
                            "content": obj.properties.get("content", ""),
                            "category": obj.properties.get("category", ""),
                            "tags": obj.properties.get("tags", []),
                            "timestamp": obj.properties.get("timestamp", ""),
                        }
                    )

            return articles
        except Exception as e:
            logger.error(f"Error finding knowledge articles: {e}")
            return []

    # Методы для работы с FAQ
    async def store_faq_entry(
        self,
        question: str,
        answer: str,
        category: str = "general",
        embedding: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Store a FAQ entry with vectorization

        Args:
            question: FAQ question
            answer: FAQ answer
            category: FAQ category
            embedding: Optional pre-computed embedding vector

        Returns:
            UUID of the created object or None if failed
        """
        try:
            # Убедимся, что класс существует
            await self._ensure_faq_class_exists()

            # Получаем коллекцию
            collection = self._client.client.collections.get("FAQ")

            # Создаем объект с нужными свойствами
            properties = {
                "question": question,
                "answer": answer,
                "category": category,
                "timestamp": self._get_current_timestamp(),
            }

            # Добавляем объект в коллекцию с вектором или без
            if embedding:
                result = collection.data.insert(
                    properties=properties, vector=embedding
                )
            else:
                # Vectorizer настроен в коллекции, так что вектор будет создан автоматически
                result = collection.data.insert(properties=properties)

            logger.info(f"Stored FAQ entry: {question[:30]}...")
            return result
        except Exception as e:
            logger.error(f"Error storing FAQ entry: {e}")
            return None

    async def find_faq_entries(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find FAQ entries related to the query

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of related FAQ entries
        """
        try:
            try:
                collection = self._client.client.collections.get("FAQ")
            except Exception as e:
                logger.error(f"Collection FAQ not found: {e}")
                await self._ensure_faq_class_exists()
                collection = self._client.client.collections.get("FAQ")

            # Используем near_text для поиска семантически похожих вопросов
            result = (
                collection.query.near_text(query=query, limit=limit)
                .with_fields(["question", "answer", "category", "timestamp"])
                .do()
            )

            # Форматируем результаты в нужный формат
            faq_entries = []
            if hasattr(result, "objects") and result.objects:
                for obj in result.objects:
                    faq_entries.append(
                        {
                            "question": obj.properties.get("question", ""),
                            "answer": obj.properties.get("answer", ""),
                            "category": obj.properties.get("category", ""),
                            "timestamp": obj.properties.get("timestamp", ""),
                        }
                    )

            return faq_entries
        except Exception as e:
            logger.error(f"Error finding FAQ entries: {e}")
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

            # Создаем схему для коллекции UserQuery с правильной конфигурацией vectorizer
            from weaviate.classes.config import Configure

            collection = self._client.client.collections.create(
                name="UserQuery",
                description="User queries to the bot",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-ada-002"
                ),
            )

            # Добавляем свойства
            collection.properties.create(
                name="user_id",
                description="Telegram user ID",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="query_text",
                description="The query text from the user",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="timestamp",
                description="When the query was made",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            logger.info("UserQuery collection created successfully")
        except Exception as e:
            logger.error(f"Error creating UserQuery class: {e}")
            # Продолжаем работу даже при ошибке

    async def _ensure_genetic_reports_class_exists(self) -> None:
        """
        Make sure the GeneticReport class exists in the schema
        """
        try:
            # Проверяем, существует ли коллекция
            try:
                self._client.client.collections.get("GeneticReport")
                # Если коллекция существует, ничего не делаем
                return
            except Exception:
                # Коллекция не существует, создаем ее
                pass

            # Создаем схему для коллекции GeneticReport с правильной конфигурацией vectorizer
            from weaviate.classes.config import Configure

            collection = self._client.client.collections.create(
                name="GeneticReport",
                description="User genetic reports from MyGenetics",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-ada-002"
                ),
            )

            # Добавляем свойства
            collection.properties.create(
                name="user_id",
                description="Telegram user ID",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="codelab",
                description="MyGenetics lab code",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="report_data",
                description="The complete genetic report data as JSON",
                data_type=self._client.client.data_type.OBJECT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="report_text",
                description="Textual representation of the report for vectorization",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="timestamp",
                description="When the report was stored",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            logger.info("GeneticReport collection created successfully")
        except Exception as e:
            logger.error(f"Error creating GeneticReport class: {e}")
            # Продолжаем работу даже при ошибке

    async def _ensure_knowledge_base_class_exists(self) -> None:
        """
        Make sure the KnowledgeBase class exists in the schema
        """
        try:
            # Проверяем, существует ли коллекция
            try:
                self._client.client.collections.get("KnowledgeBase")
                # Если коллекция существует, ничего не делаем
                return
            except Exception:
                # Коллекция не существует, создаем ее
                pass

            # Создаем схему для коллекции KnowledgeBase с правильной конфигурацией vectorizer
            from weaviate.classes.config import Configure

            collection = self._client.client.collections.create(
                name="KnowledgeBase",
                description="Knowledge base articles and methodical data",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-ada-002"
                ),
            )

            # Добавляем свойства
            collection.properties.create(
                name="title",
                description="Article title",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="content",
                description="Article content",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="category",
                description="Article category",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="tags",
                description="Article tags",
                data_type=self._client.client.data_type.TEXT_ARRAY,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="timestamp",
                description="When the article was created or updated",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            logger.info("KnowledgeBase collection created successfully")
        except Exception as e:
            logger.error(f"Error creating KnowledgeBase class: {e}")
            # Продолжаем работу даже при ошибке

    async def _ensure_faq_class_exists(self) -> None:
        """
        Make sure the FAQ class exists in the schema
        """
        try:
            # Проверяем, существует ли коллекция
            try:
                self._client.client.collections.get("FAQ")
                # Если коллекция существует, ничего не делаем
                return
            except Exception:
                # Коллекция не существует, создаем ее
                pass

            # Создаем схему для коллекции FAQ с правильной конфигурацией vectorizer
            from weaviate.classes.config import Configure

            collection = self._client.client.collections.create(
                name="FAQ",
                description="Frequently asked questions",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-ada-002"
                ),
            )

            # Добавляем свойства
            collection.properties.create(
                name="question",
                description="FAQ question",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="answer",
                description="FAQ answer",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=False,
            )

            collection.properties.create(
                name="category",
                description="FAQ category",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            collection.properties.create(
                name="timestamp",
                description="When the FAQ entry was created or updated",
                data_type=self._client.client.data_type.TEXT,
                skip_vectorization=True,
            )

            logger.info("FAQ collection created successfully")
        except Exception as e:
            logger.error(f"Error creating FAQ class: {e}")
            # Продолжаем работу даже при ошибке

    def _format_report_as_text(self, report_data: Dict[str, Any]) -> str:
        """
        Format report data as text for vectorization

        Args:
            report_data: Genetic report data

        Returns:
            Text representation of the report
        """
        # Here we would format the report data as text
        # This is a simple implementation - in practice, you'd want to create a detailed
        # text representation of the genetic report that captures all important information
        text_parts = []

        if isinstance(report_data, dict):
            for key, value in report_data.items():
                # Handle nested dictionaries
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        text_parts.append(f"{key} - {sub_key}: {sub_value}")
                # Handle lists
                elif isinstance(value, list):
                    list_items = ", ".join(str(item) for item in value)
                    text_parts.append(f"{key}: {list_items}")
                # Handle simple values
                else:
                    text_parts.append(f"{key}: {value}")

        return "\n".join(text_parts)

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.now().isoformat()
