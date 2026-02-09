import os, subprocess
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from db.models import Tenant, Conversation, Message

def _print_commit():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
    except Exception as e:
        sha = f"no-git ({e})"
    print("[WORKER] CODE VERSION:", sha)

_print_commit()

def save_incoming(payload: dict, tenant_id: str = "demo") -> str:
    """
    Guarda payload entrante:
    - upsert tenant
    - upsert conversation por (tenant_id, wa_id)
    - inserta message direction=in con raw=payload
    Devuelve conversation_id (uuid str)
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_engine(url, pool_pre_ping=True)

    # wa_id: por ahora soporta payload simulado y distintos formatos
    wa_id = (
        payload.get("wa_id")
        or payload.get("from")
        or payload.get("contacts", [{}])[0].get("wa_id")
        or "unknown"
    )

    with Session(engine) as session:
        # tenant
        t = session.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if not t:
            t = Tenant(id=tenant_id, name="Demo")
            session.add(t)
            session.commit()

        # conversation
        conv = session.scalar(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.wa_id == wa_id,
            )
        )
        if not conv:
            conv = Conversation(tenant_id=tenant_id, wa_id=wa_id, status="new")
            session.add(conv)
            session.commit()
            session.refresh(conv)

        # message in
        text = payload.get("text") or payload.get("body") or payload.get("message") or ""
        session.add(
            Message(
                conversation_id=conv.id,
                direction="in",
                text=text,
                raw=payload,
            )
        )
        session.commit()

        return str(conv.id)


def process_payload(payload: dict):
    """
    Función que ejecuta el worker (RQ).
    """
    print("[WORKER] got payload:", payload)
    conv_id = save_incoming(payload, tenant_id="demo")
    print("[WORKER] saved incoming. conv_id:", conv_id)
    return {"ok": True, "conversation_id": conv_id}

def handle_incoming(payload: dict):
    print("[WORKER] got payload:", payload)
    conv_id = save_incoming(payload, tenant_id="demo")
    print("[WORKER] saved incoming. conv_id:", conv_id)
    return {"ok": True, "conversation_id": conv_id}

