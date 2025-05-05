from pymongo import MongoClient
from src.app.core.containers import Container
from dependency_injector.wiring import inject, Provide


@inject
def get_mongo_client(container: Container = Provide[Container.mongo_client]):
    return MongoClient(
        host=container.config.mongodb.MONGO_HOST,
        port=container.config.mongodb.MONGO_PORT,
        username=container.config.mongodb.MONGO_USER,
        password=container.config.mongodb.MONGO_PASS,
    )


@inject
def get_mongo_db(container: Container = Provide[Container.mongo_client]):
    client = get_mongo_client(container)
    return client["resume_generator"]


@inject
def get_mongo_collection(
    collection_name: str,
    container: Container = Provide[Container.mongo_client],
):
    db = get_mongo_db(container)
    return db[collection_name]
