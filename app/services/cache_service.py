from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading

class CacheService:
    def __init__(self, default_ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry['expires_at']:
                    return entry['value']
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        with self.lock:
            ttl = ttl_seconds or self.default_ttl
            expires_at = datetime.now() + timedelta(seconds=ttl)
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
    
    def delete(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self):
        with self.lock:
            now = datetime.now()
            expired_keys = [key for key, entry in self.cache.items() 
                          if now >= entry['expires_at']]
            for key in expired_keys:
                del self.cache[key]

