from app.config.settings import global_settings
import ujson
import time
from typing import TypeVar, Optional, Dict
import redis.asyncio as aioredis


T = TypeVar("T")


class RedisInstanceManager:
    _instances: Dict[int, aioredis.Redis] = {}

    @classmethod
    def get_redis_instance(
        cls, db: int, host: str, port: int, username: Optional[str] = None, password: Optional[str]=None, max_connections: int = 5000) -> aioredis.Redis:
        if db not in cls._instances:
            pool = aioredis.ConnectionPool(
                username=username,
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=False,  # 不自动解码数据
                max_connections=max_connections,  # 限制连接数
            )
            redis_client = aioredis.Redis(connection_pool=pool)
            cls._instances[db] = redis_client
        return cls._instances[db]

    @classmethod
    async def close_all(cls):
        for redis_instance in cls._instances.values():
            # 关闭 Redis 实例（自动处理连接池）
            await redis_instance.close()
        cls._instances.clear()


# 创建 AsyncRedisStorage 默认实例
async_redis_storage =RedisInstanceManager.get_redis_instance(
    db=global_settings.redis.db,
    host=global_settings.redis.host,
    port=global_settings.redis.port,
    username=global_settings.redis.user,
    password=global_settings.redis.password,
    max_connections=5000
)