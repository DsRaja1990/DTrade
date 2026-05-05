"""
Redis client configuration
"""

import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with async support"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.url = settings.REDIS_URL
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.ping()
            logger.info("✅ Redis connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        try:
            if self.redis:
                await self.redis.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    async def set(
        self,
        key: str,
        value: Union[str, dict, list, int, float],
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in Redis"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await self.redis.set(key, value, ex=ttl)
            return result
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def get(self, key: str, parse_json: bool = False) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = await self.redis.get(key)
            
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            result = await self.redis.expire(key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    async def hset(self, name: str, key: str, value: Union[str, dict, list]) -> bool:
        """Set hash field"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await self.redis.hset(name, key, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis hset error: {e}")
            return False
    
    async def hget(self, name: str, key: str, parse_json: bool = False) -> Optional[Any]:
        """Get hash field"""
        try:
            value = await self.redis.hget(name, key)
            
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except Exception as e:
            logger.error(f"Redis hget error: {e}")
            return None
    
    async def hgetall(self, name: str, parse_json: bool = False) -> dict:
        """Get all hash fields"""
        try:
            data = await self.redis.hgetall(name)
            
            if parse_json:
                parsed_data = {}
                for key, value in data.items():
                    try:
                        parsed_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        parsed_data[key] = value
                return parsed_data
            
            return data
        except Exception as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}
    
    async def hdel(self, name: str, key: str) -> bool:
        """Delete hash field"""
        try:
            result = await self.redis.hdel(name, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis hdel error: {e}")
            return False
    
    async def lpush(self, key: str, *values: Union[str, dict, list]) -> int:
        """Push values to list"""
        try:
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value))
                else:
                    processed_values.append(str(value))
            
            result = await self.redis.lpush(key, *processed_values)
            return result
        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return 0
    
    async def rpop(self, key: str, parse_json: bool = False) -> Optional[Any]:
        """Pop value from list"""
        try:
            value = await self.redis.rpop(key)
            
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except Exception as e:
            logger.error(f"Redis rpop error: {e}")
            return None
    
    async def llen(self, key: str) -> int:
        """Get list length"""
        try:
            result = await self.redis.llen(key)
            return result
        except Exception as e:
            logger.error(f"Redis llen error: {e}")
            return 0
    
    async def publish(self, channel: str, message: Union[str, dict, list]) -> int:
        """Publish message to channel"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            
            result = await self.redis.publish(channel, message)
            return result
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return 0
    
    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe error: {e}")
            return None
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment key value"""
        try:
            result = await self.redis.incr(key, amount)
            return result
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement key value"""
        try:
            result = await self.redis.decr(key, amount)
            return result
        except Exception as e:
            logger.error(f"Redis decr error: {e}")
            return 0


# Create global Redis client instance
redis_client = RedisClient()
