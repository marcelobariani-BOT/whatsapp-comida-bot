import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.queue import get_queue

app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/debug/enqueue")
async def debug_enqueue(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    q = get_queue()
    from app.workers.responder import process_payload  # lazy import
    job = q.enqueue(process_payload, payload)

    return {"ok": True, "job_id": job.id}


@app.post("/wa/webhook")
async def wa_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    q = get_queue()
    from app.workers.responder import process_payload  # lazy import
    job = q.enqueue(process_payload, payload)

    return {"ok": True, "job_id": job.id}


@app.get("/wa/webhook")
def wa_webhook_verify(request: Request):
    mode = (request.query_params.get("hub.mode") or "").strip()
    token = (request.query_params.get("hub.verify_token") or "").strip()
    challenge = request.query_params.get("hub.challenge")

    verify_token = (os.getenv("META_VERIFY_TOKEN") or "").strip()

    print("[META-VERIFY]", {"mode": mode, "token": token, "challenge": challenge})

    if mode == "subscribe" and token and verify_token and token == verify_token and challenge:
        return JSONResponse(content=int(challenge))

    return JSONResponse(status_code=403, content={"ok": False})
