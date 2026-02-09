from fastapi import FastAPI, Request
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

@app.post("/wa/webhook")
async def wa_webhook(request: Request):
    payload = await request.json()
    q = get_queue()
    job = q.enqueue("app.workers.responder.handle_incoming", payload)
    return {"ok": True, "job_id": job.id}

