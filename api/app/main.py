import os
from fastapi import Query
from fastapi.responses import PlainTextResponse
from fastapi import FastAPI, Request, HTTPException
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
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or empty JSON body")

    q = get_queue()
    job = q.enqueue("app.workers.responder.handle_incoming", payload)
    return {"ok": True, "job_id": job.id}

@app.get("/wa/webhook")
async def wa_webhook_verify(request: Request):
    qp = request.query_params
    mode = (qp.get("hub.mode") or "").strip()
    token = (qp.get("hub.verify_token") or "").strip()
    challenge = (qp.get("hub.challenge") or "").strip()

    expected = (os.environ.get("META_VERIFY_TOKEN") or "").strip()

    # log para ver qué llega (Render logs)
    print(f"[META-VERIFY] mode={mode!r} token={token!r} expected={expected!r} challenge={challenge!r}")

    if mode == "subscribe" and token == expected:
        return PlainTextResponse(challenge)
    return PlainTextResponse("forbidden", status_code=403)


