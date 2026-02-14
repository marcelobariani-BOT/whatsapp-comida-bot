import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.queue import get_queue
from sqlalchemy import text
from sqlalchemy import create_engine

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

@app.get("/debug/db-check")
def debug_db_check():
    url = os.getenv("DATABASE_URL")
    if not url:
        return {"ok": False, "error": "DATABASE_URL not set"}

    engine = create_engine(url, pool_pre_ping=True)

    with engine.connect() as conn:
        # chequea si existe conversation_state en schema public
        exists = conn.execute(text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public'
                AND table_name = 'conversation_state'
            ) AS exists;
        """)).scalar_one()

        return {"ok": True, "conversation_state_exists": bool(exists)}
        
@app.get("/debug/db-info")
def debug_db_info():
    url = os.getenv("DATABASE_URL")
    if not url:
        return {"ok": False, "error": "DATABASE_URL not set"}

    engine = create_engine(url, pool_pre_ping=True)

    with engine.connect() as conn:
        # alembic version
        try:
            alembic_version = conn.execute(text("select version_num from alembic_version")).scalar()
        except Exception as ex:
            alembic_version = f"NO alembic_version table ({ex})"

        # search conversation_state in any schema
        rows = conn.execute(text("""
            select table_schema, table_name
            from information_schema.tables
            where table_name = 'conversation_state'
            order by table_schema
        """)).all()

        current_schema = conn.execute(text("select current_schema()")).scalar()

        return {
            "ok": True,
            "alembic_version": alembic_version,
            "conversation_state_tables": [{"schema": r[0], "table": r[1]} for r in rows],
            "current_schema": current_schema,
        }
