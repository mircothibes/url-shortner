# app/cache.py
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def get_url_from_cache_or_db(short_code: str, db: Session):
    # Try Redis first
    cache_key = f"url:{short_code}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Cache miss: query PostgreSQL
    url = db.query(URL).filter(URL.short_code == short_code).first()
    
    if url:
        # Cache for 1 hour
        redis_client.setex(
            cache_key,
            timedelta(hours=1).total_seconds(),
            json.dumps(url.to_dict())
        )
    
    return url

# Rate limiting via Redis
def rate_limit_check(user_id: str, limit: int = 100, window: int = 3600):
    """
    Token bucket algorithm: 100 requests per hour
    """
    key = f"rate_limit:{user_id}"
    current = redis_client.incr(key)
    
    if current == 1:
        redis_client.expire(key, window)
    
    if current > limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    return current
