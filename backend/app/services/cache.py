"""Тонка обгортка над Redis для кешування розкладів (ТЗ, MVP-5).

Ключі: schedule:{scope}:{id}. Кеш не обовʼязковий для роботи API — якщо Redis
недоступний, усі операції тихо стають no-op, а дані беруться з БД.
"""

import json
from collections.abc import Iterable

import redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_client() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            _client.ping()
        except (redis.RedisError, OSError):
            _client = None
    return _client


def _key(scope: str, scope_id: int | str) -> str:
    return f"schedule:{scope}:{scope_id}"


def get_cached(scope: str, scope_id: int | str) -> list | dict | None:
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(_key(scope, scope_id))
    except redis.RedisError:
        return None
    return json.loads(raw) if raw else None


def set_cached(scope: str, scope_id: int | str, value: list | dict, ttl: int = 3600) -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.set(_key(scope, scope_id), json.dumps(value, default=str), ex=ttl)
    except redis.RedisError:
        pass


def invalidate(pairs: Iterable[tuple[str, int | str]]) -> None:
    """Скидає перелічені ключі (scope, id) після будь-якої зміни заняття."""
    client = get_client()
    if client is None:
        return
    keys = [_key(scope, scope_id) for scope, scope_id in pairs]
    if keys:
        try:
            client.delete(*keys)
        except redis.RedisError:
            pass
