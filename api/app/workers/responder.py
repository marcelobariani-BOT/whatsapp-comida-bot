import os
import subprocess
from typing import Any, Dict, Tuple

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Tenant, Conversation, Message


def _print_commit():
    try:
        sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )
    except Exception as e:
        sha = f"no-git ({e})"
    print("[WORKER] CODE VERSION:", sha)


_print_commit()

# ✅ Crear engine 1 vez (no por job)
_DATABASE_URL = os.getenv("DATABASE_URL")
if not _DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

ENGINE = create_engine(_DATABASE_URL, pool_pre_ping=True)


def normalize_internal_payload(payload: Dict[str, Any]) -> Tuple[str, str, str, Dict[str, Any]]:
    """
    Normaliza el payload al formato interno.
    Esperado:
      - tenant_id (opcional, default 'demo')
      - wa_id (obligatorio)
      - text (obligatorio)
      - raw (opcional, default payload completo)

    Devuelve: (tenant_id, wa_id, text, raw)
    """
    tenant_id = (payload.get("tenant_id") or "demo").strip()

    wa_id = payload.get("wa_id")
    text = payload.get("text")

    # Si viene en mock simple, ok.
    # Si viene de algún test viejo, permitimos algunos alias (pero NO "unknown"):
    if not wa_id:
        wa_id = payload.get("from") or payload.get("waId")

    if text is None:
        # Permitimos alias por compatibilidad con pruebas anteriores
        text = payload.get("body") or payload.get("message")

    raw = payload.get("raw")
    if raw is None:
        # Si no te pasan raw, guardamos el payload completo
        raw = payload

    # Validación mínima
    if not wa_id or not str(wa_id).strip():
        raise ValueError("Payload inválido: falta 'wa_id'")
    if text is None:
        raise ValueError("Payload inválido: falta 'text'")
    text = str(text)

    return tenant_id, str(wa_id).strip(), text, raw


def save_incoming(payload: Dict[str, Any]) -> str:
    """
    Guarda payload entrante usando formato interno:
      - upsert tenant
      - upsert conversation por (tenant_id, wa_id)
      - inserta message direction=in con text y raw
    Devuelve conversation_id (uuid str)
    """
    tenant_id, wa_id, text, raw = normalize_internal_payload(payload)

    with Session(ENGINE) as session:
        # tenant upsert
        t = session.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if not t:
            t = Tenant(id=tenant_id, name="Demo")
            session.add(t)
            session.commit()

        # conversation upsert (tenant_id, wa_id)
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
        session.add(
            Message(
                conversation_id=conv.id,
                direction="in",
                text=text,
                raw=raw,
            )
        )
        session.commit()

        return str(conv.id)


def process_payload(payload: Dict[str, Any]):
    """Función que ejecuta el worker (RQ)."""
    print("[WORKER] got payload:", payload)
    conv_id = save_incoming(payload)
    print("[WORKER] saved incoming. conv_id:", conv_id)
    return {"ok": True, "conversation_id": conv_id}


# Alias opcional (por si en algún lado llamás handle_incoming)
def handle_incoming(payload: Dict[str, Any]):
    return process_payload(payload)
