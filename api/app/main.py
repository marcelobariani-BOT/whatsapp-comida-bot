from fastapi import FastAPI
from app.queue import get_queue

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/debug/enqueue")
def debug_enqueue():
    q = get_queue()
    job = q.enqueue("app.workers.responder.handle_incoming", {"hello": "world"})
    return {"enqueued": True, "job_id": job.id}

