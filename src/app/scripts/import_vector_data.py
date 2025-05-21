#!/usr/bin/env python3
"""
Script for importing sample data into Weaviate vector storage.
- FAQ entries
- Knowledge base articles
- Sample genetic reports
"""

import asyncio
import logging
import json
import sys
import os

# Add the project root to the Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
)

from src.app.core.containers import Container
from src.app.core.config import settings
from src.app.services.vector_storage_service import VectorStorageService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Sample FAQ entries
SAMPLE_FAQ = [
    {
        "question": "Что такое MyGenetics?",
        "answer": "MyGenetics — это сервис персонализированных генетических исследований, который анализирует ваш ДНК-профиль и предоставляет рекомендации по питанию, физической активности и образу жизни на основе ваших генетических особенностей.",
        "category": "general",
    },
    {
        "question": "Как работает генетический тест?",
        "answer": "Генетический тест анализирует определенные участки вашей ДНК, чтобы выявить генетические варианты, связанные с метаболизмом, усвоением питательных веществ, предрасположенностью к различным заболеваниям и другими важными характеристиками. На основе этих данных формируются персонализированные рекомендации.",
        "category": "testing",
    },
    {
        "question": "Как часто нужно проходить генетический тест?",
        "answer": "Генетический тест достаточно пройти один раз в жизни, поскольку ваша ДНК не меняется. Однако рекомендации могут обновляться по мере появления новых научных данных о влиянии генетических вариантов на здоровье и метаболизм.",
        "category": "testing",
    },
    {
        "question": "Что такое лабкод и где его найти?",
        "answer": "Лабкод — это уникальный идентификатор вашего генетического теста. Вы можете найти его в вашем личном кабинете на сайте MyGenetics или в письме, которое вы получили после прохождения тестирования.",
        "category": "accounts",
    },
    {
        "question": "Могу ли я получить рекомендации по питанию без генетического теста?",
        "answer": "Бот может предоставить общие рекомендации по здоровому питанию без генетического теста. Однако для получения персонализированных рекомендаций, учитывающих ваши генетические особенности, необходимо пройти тестирование и авторизоваться с вашим лабкодом.",
        "category": "nutrition",
    },
]

# Sample knowledge base articles
SAMPLE_KNOWLEDGE_BASE = [
    {
        "title": "Правильное питание и генетика",
        "content": "Генетические особенности могут влиять на то, как ваш организм реагирует на различные продукты. Например, люди с определенными генетическими вариантами могут быть более чувствительны к углеводам, жирам или лактозе. Персонализированное питание, учитывающее ваш генетический профиль, может помочь оптимизировать ваше здоровье и достичь желаемого веса.",
        "category": "nutrition",
        "tags": ["питание", "генетика", "метаболизм", "персонализация"],
    },
    {
        "title": "Физическая активность и генетика",
        "content": "Ваши гены могут определять, какой тип физической активности будет наиболее эффективным для вас. Некоторые люди генетически предрасположены к силовым тренировкам, в то время как другие могут получить больше пользы от аэробных упражнений. Понимание вашего генетического профиля может помочь разработать оптимальную программу тренировок.",
        "category": "fitness",
        "tags": ["фитнес", "тренировки", "генетика", "спорт"],
    },
    {
        "title": "Метаболизм витаминов и микроэлементов",
        "content": "Генетические вариации могут влиять на способность вашего организма усваивать, транспортировать и использовать различные витамины и минералы. Например, некоторые люди могут иметь генетическую предрасположенность к дефициту витамина D, B12 или железа, независимо от диеты. Персонализированные рекомендации по приему добавок могут помочь компенсировать эти генетические особенности.",
        "category": "nutrition",
        "tags": ["витамины", "микроэлементы", "добавки", "метаболизм"],
    },
    {
        "title": "Генетика и интолерантность к лактозе",
        "content": "Непереносимость лактозы часто имеет генетическую основу. Люди с определенными генетическими вариантами производят меньше фермента лактазы, необходимого для расщепления лактозы — сахара, содержащегося в молочных продуктах. Если у вас генетическая предрасположенность к непереносимости лактозы, вам может быть рекомендовано ограничить потребление молочных продуктов или принимать ферментные добавки.",
        "category": "nutrition",
        "tags": [
            "лактоза",
            "непереносимость",
            "молочные продукты",
            "пищеварение",
        ],
    },
    {
        "title": "Генетика и метаболизм кофеина",
        "content": "Скорость, с которой ваш организм метаболизирует кофеин, может быть определена генетически. 'Быстрые метаболизаторы' кофеина могут пить кофе даже вечером без влияния на сон, в то время как 'медленные метаболизаторы' могут испытывать бессонницу и беспокойство даже от небольшого количества кофеина, потребляемого днем. Понимание вашего генетического профиля метаболизма кофеина может помочь оптимизировать потребление кофеина.",
        "category": "nutrition",
        "tags": ["кофеин", "метаболизм", "кофе", "сон"],
    },
]

# Sample genetic report (simplified structure)
SAMPLE_GENETIC_REPORT = {
    "user_id": "sample_user_123",
    "codelab": "DEMO123456",
    "report_data": {
        "metabolism": {
            "carbohydrate_sensitivity": "high",
            "fat_metabolism": "normal",
            "protein_utilization": "efficient",
        },
        "vitamins": {
            "vitamin_d": "reduced synthesis",
            "vitamin_b12": "normal absorption",
            "folate": "increased need",
        },
        "fitness": {
            "endurance": "genetically predisposed",
            "power": "normal response",
            "recovery_rate": "slow",
        },
        "intolerances": {
            "lactose": "likely intolerant",
            "gluten": "no genetic risk",
            "caffeine": "slow metabolizer",
        },
    },
}


async def import_data():
    """Import sample data into Weaviate"""
    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "src.app.services.vector_storage_service",
        ]
    )

    # Create VectorStorageService
    vector_storage_service = container.vector_storage_service()

    # Import FAQ entries
    logger.info("Importing FAQ entries...")
    for faq in SAMPLE_FAQ:
        try:
            result = await vector_storage_service.store_faq_entry(
                question=faq["question"],
                answer=faq["answer"],
                category=faq["category"],
            )
            logger.info(f"Imported FAQ: {faq['question'][:30]}...")
        except Exception as e:
            logger.error(f"Error importing FAQ: {e}")

    # Import knowledge base articles
    logger.info("Importing knowledge base articles...")
    for article in SAMPLE_KNOWLEDGE_BASE:
        try:
            result = await vector_storage_service.store_knowledge_article(
                title=article["title"],
                content=article["content"],
                category=article["category"],
                tags=article["tags"],
            )
            logger.info(f"Imported article: {article['title']}")
        except Exception as e:
            logger.error(f"Error importing article: {e}")

    # Import sample genetic report
    logger.info("Importing sample genetic report...")
    try:
        result = await vector_storage_service.store_genetic_report(
            user_id=SAMPLE_GENETIC_REPORT["user_id"],
            codelab=SAMPLE_GENETIC_REPORT["codelab"],
            report_data=SAMPLE_GENETIC_REPORT["report_data"],
        )
        logger.info(
            f"Imported sample genetic report for user {SAMPLE_GENETIC_REPORT['user_id']}"
        )
    except Exception as e:
        logger.error(f"Error importing sample genetic report: {e}")

    logger.info("Import completed!")


if __name__ == "__main__":
    asyncio.run(import_data())
