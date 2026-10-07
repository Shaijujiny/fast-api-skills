"""Lazy MongoDB client; nothing connects until first use."""

from functools import lru_cache

from app.database.mongodb.config import MongoSettings


@lru_cache
def get_client():
    from pymongo import MongoClient  # imported lazily so pymongo stays optional

    return MongoClient(MongoSettings().url)


def get_database():
    return get_client()[MongoSettings().name]
