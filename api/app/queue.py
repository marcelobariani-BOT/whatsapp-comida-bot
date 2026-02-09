import os
import redis
from rq import Queue

def get_queue() -> Queue:
    conn = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    return Queue(name=os.getenv("QUEUE_NAME", "wa"), connection=conn)
