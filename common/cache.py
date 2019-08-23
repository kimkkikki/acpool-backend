from werkzeug.contrib.cache import MemcachedCache, NullCache
import os

if os.getenv("DEBUG") == 'true':
    cache = NullCache()
else:
    cache = MemcachedCache()
