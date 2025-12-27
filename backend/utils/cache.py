"""Simple in-memory cache with TTL"""
from typing import Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

class SimpleCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: dict = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry['expires_at']:
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + self.ttl
        }
    
    def clear(self) -> None:
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)

response_cache = SimpleCache(ttl_seconds=3600)