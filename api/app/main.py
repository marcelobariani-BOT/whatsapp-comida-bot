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
def wa_webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    expected = (os.environ.get("META_VERIFY_TOKEN") or "").strip()
    received = (hub_verify_token or "").strip()

    # Debug útil (sale en logs)
    print(f"[VERIFY] mode={hub_mode} received={received!r} expected={expected!r}")

    if hub_mode == "subscribe" and received == expected:
        return PlainTextResponse(hub_challenge or "")
    return PlainTextResponse("forbidden", status_code=403)



