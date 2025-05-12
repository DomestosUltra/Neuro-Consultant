import logging
from typing import List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def generate_embedding(
    text: str, client: AsyncOpenAI, model: str = "text-embedding-3-small"
) -> Optional[List[float]]:
    """
    Generate an embedding vector for text using OpenAI's embedding API

    Args:
        text: The text to generate an embedding for
        client: OpenAI client instance
        model: The embedding model to use

    Returns:
        List of floats representing the embedding vector or None if failed
    """
    try:
        # Truncate text if too long (OpenAI has a token limit)
        if len(text) > 8000:
            text = text[:8000]

        response = await client.embeddings.create(
            model=model, input=text, encoding_format="float"
        )

        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None
