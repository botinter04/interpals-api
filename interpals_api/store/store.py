import redis
import json
from typing import Optional, Any
from ..configs import Config


class RedisClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, password: Optional[str] = None, db: int = 0):
        try:
            self.client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
            self.client.ping()
            print("Connected to Redis successfully.")
        except redis.RedisError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Stores a key-value pair in Redis. Optionally set an expiration time (in seconds).
        Value will be stored as a JSON string.
        """
        try:
            json_value = json.dumps(value)
            self.client.set(name=key, value=json_value, ex=expire)
            return True
        except redis.RedisError as e:
            print(f"faled to set key in redis: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value by key from Redis. Returns the parsed JSON object or None if not found.
        """
        try:
            value = self.client.get(name=key)
            if value is None:
                return None
            return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"failed to get key from redis: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete value of key from redis.
        """
        try:
            self.client.delete(*key)
            return True
        except redis.RedisError as e:
            print(f"failed to delete key from redis: {e}")
            return False

    def count_keys_with_prefix(self, prefix: str) -> int:
        """
        Count the number of keys in Redis that start with a specific prefix using SCAN.
        """
        try:
            count = 0
            cursor = 0
            pattern = f"{prefix}*"
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)
                count += len(keys)
                if cursor == 0:
                    break
            return count
        except redis.RedisError as e:
            print(f"Failed to count keys with prefix '{prefix}': {e}")
            return 0
        
    def get_values_with_prefix(self, prefix: str) -> list:
        """
        Returns a list of all values from Redis where keys start with the given prefix.
        """
        try:
            values = []
            cursor = 0
            pattern = f"{prefix}*"
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)
                for key in keys:
                    value = self.get(key)
                    if value is not None:
                        values.append(json.loads(value))
                if cursor == 0:
                    break
            return values
        except redis.RedisError as e:
            print(f"Failed to get values with prefix '{prefix}': {e}")
            return []

redis_client = RedisClient(Config.REDIS_HOST, int(Config.REDIS_PORT))