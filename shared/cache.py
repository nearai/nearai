import time
from functools import wraps


def mem_cache_with_timeout(timeout: int):
    """Decorator to cache function results for a specified timeout period."""

    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = (args, frozenset(kwargs.items()))
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < timeout:
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result

        return wrapper

    return decorator
