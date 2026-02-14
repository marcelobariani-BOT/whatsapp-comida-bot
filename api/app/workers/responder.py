import os
import subprocess
from typing import Any, Dict, Tuple

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from db.models import Tenant, Conversation, Message
from db.state import ConversationState


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

_DATABASE_URL = os.getenv("DATABASE_URL")
if not _DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

ENGINE = create_engine(_DATABASE_URL, pool_pre_ping=True)


def normalize_internal_payload(payload: Dict[str, Any]) -> Tuple[str, str, str, Dict[str, Any]]:
    tenant_id = (payload.get("tenant_id") or "demo").strip()
    wa_id = payload.get("wa_id") or payload.get("from") or payload.get("waId")
    text = payload.get("text")
    if text is None:
        text = payload.get("body") or payload.get("message")

    raw = payload.get("raw")
    if raw is None:
        raw = payload

    if not wa_id or not str(wa_id).strip():
        raise ValueError("Payload inválido: falta 'wa_id'")
    if text is None:
        raise ValueError("Payload inválido: falta 'text'")

    return tenant_id, str(wa_id).strip(), str(text), raw


# ---------------------------
# Lógica de conversación (estado)
# ---------------------------

def detect_intent(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["pizza", "muzza", "muzzarella", "napo", "napolitana", "fugazza", "calabresa"]):
        return "ORDER_PIZZA"
    if "empan" in t:
        return "ORDER_EMPANADAS"
    if any(w in t for w in ["coca", "pepsi", "agua", "gaseosa", "bebida"]):
        return "ORDER_DRINK"
    if any(w in t for w in ["si", "sí", "dale", "ok", "confirmo", "confirmar"]):
        return "CONFIRM"
    if any(w in t for w in ["no", "cancela", "cancelar"]):
        return "CANCEL"
    return "UNKNOWN"


def extract_slots(text: str) -> Dict[str, Any]:
    """Extrae datos simples del texto."""
    t = (text or "").lower()

    size = None
    if any(w in t for w in ["grande", "gigante"]):
        size = "grande"
    elif any(w in t for w in ["chica", "pequeña", "pequena"]):
        size = "chica"

    delivery = None
    if any(w in t for w in ["retiro", "retirar", "paso a buscar"]):
        delivery = "retiro"
    elif any(w in t for w in ["envio", "envío", "delivery", "mandalo", "enviar"]):
        delivery = "envio"

    # dirección: heurística simple (si contiene "calle" o número)
    address = None
    if any(w in t for w in ["calle", "av", "avenida", "altura", "nro", "numero", "número"]):
        address = text.strip()
    # si el usuario manda algo largo que no parece tamaño/delivery, lo tomamos como dirección cuando stage lo pida
    if len(t.strip()) >= 10 and not size and not delivery:
        address = text.strip()

    # gusto pizza
    flavor = None
    if any(w in t for w in ["muzza", "muzzarella"]):
        flavor = "muzza"
    elif "napo" in t:
        flavor = "napolitana"
    elif "fugazz" in t:
        flavor = "fugazza"
    elif "calab" in t:
        flavor = "calabresa"

    return {"size": size, "delivery": delivery, "address": address, "flavor": flavor}


def next_step(stage: str, state: Dict[str, Any], text: str) -> Tuple[str, Dict[str, Any], str]:
    """
    Máquina de estados mínima para PIZZA.
    stage: NEW | ASK_FLAVOR | ASK_SIZE | ASK_DELIVERY | ASK_ADDRESS | CONFIRM | DONE
    state: {"order": {"item":"pizza","flavor":"muzza","size":"grande","delivery":"envio","address":"..." }}
    """
    intent = detect_intent(text)
    slots = extract_slots(text)

    order = state.get("order") or {}
    if not order:
        state["order"] = order

    # Cancelación
    if intent == "CANCEL":
        state["order"] = {}
        return "NEW", state, "Ok, cancelado 👍 ¿Querés arrancar un pedido nuevo?"

    # Si estamos en NEW, arrancamos con pizza si lo detectamos
    if stage == "NEW":
        if intent == "ORDER_PIZZA":
            order["item"] = "pizza"
            if slots["flavor"]:
                order["flavor"] = slots["flavor"]
                return "ASK_SIZE", state, "Genial 🍕 ¿La querés grande o chica?"
            return "ASK_FLAVOR", state, "Dale 🍕 ¿Qué pizza querés? (muzza / napolitana / fugazza / calabresa)"
        return "NEW", state, "¡Hola! 😄 ¿Qué te gustaría pedir hoy? (pizza / empanadas / bebidas)"

    if stage == "ASK_FLAVOR":
        if slots["flavor"]:
            order["flavor"] = slots["flavor"]
            return "ASK_SIZE", state, "Perfecto. ¿La querés grande o chica?"
        return "ASK_FLAVOR", state, "¿De qué gusto? (muzza / napolitana / fugazza / calabresa)"

    if stage == "ASK_SIZE":
        if slots["size"]:
            order["size"] = slots["size"]
            return "ASK_DELIVERY", state, "¿Es para retiro o envío?"
        return "ASK_SIZE", state, "¿Grande o chica?"

    if stage == "ASK_DELIVERY":
        # ✅ Si manda una dirección sin decir "envío", asumimos ENVÍO automáticamente
        if slots["address"] and not slots["delivery"]:
            order["delivery"] = "envio"
            order["address"] = slots["address"]
            return (
                "CONFIRM",
                state,
                f"Perfecto ✅ {order.get('flavor','pizza')} {order.get('size','')} para ENVÍO a “{order['address']}”. ¿Confirmás? (sí/no)",
            )

    if slots["delivery"]:
        order["delivery"] = slots["delivery"]
        if order["delivery"] == "retiro":
            return (
                "CONFIRM",
                state,
                f"Listo ✅ {order.get('flavor','pizza')} {order.get('size','')} para RETIRO. ¿Confirmás? (sí/no)",
            )
        return "ASK_ADDRESS", state, "Ok 🚚 Pasame la dirección completa para el envío."

    return "ASK_DELIVERY", state, "¿Retiro o envío?"


    if stage == "ASK_ADDRESS":
        # acá tomamos address sí o sí si es algo mínimamente largo
        addr = slots["address"] or text.strip()
        if addr and len(addr) >= 6:
            order["address"] = addr
            return "CONFIRM", state, f"Perfecto ✅ {order.get('flavor','pizza')} {order.get('size','')} para ENVÍO a “{addr}”. ¿Confirmás? (sí/no)"
        return "ASK_ADDRESS", state, "Necesito la dirección completa (calle y número)."

    if stage == "CONFIRM":
        if intent == "CONFIRM":
            # acá después creamos Order real; por ahora cerramos
            return "DONE", state, "¡Genial! 🎉 Pedido confirmado. En breve te avisamos el tiempo estimado."
        if intent == "CANCEL":
            state["order"] = {}
            return "NEW", state, "Ok, cancelado 👍 ¿Querés pedir otra cosa?"
        return "CONFIRM", state, "Decime “sí” para confirmar o “no” para cancelar."

    if stage == "DONE":
        # Si escribe de nuevo, reiniciamos soft
        if intent == "ORDER_PIZZA":
            state["order"] = {}
            return "NEW", state, "Dale, armemos otro pedido. ¿Qué pizza querés?"
        return "DONE", state, "¿Querés agregar algo más? (pizza / empanadas / bebidas)"

    return "NEW", state, "Te leo 🙂 ¿Qué querés pedir?"


# ---------------------------
# DB: guardar y avanzar estado
# ---------------------------

def save_incoming_and_reply(payload: Dict[str, Any]) -> Tuple[str, str]:
    tenant_id, wa_id, text, raw = normalize_internal_payload(payload)

    with Session(ENGINE) as session:
        # tenant upsert
        t = session.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if not t:
            t = Tenant(id=tenant_id, name="Demo")
            session.add(t)
            session.commit()

        # conversation upsert
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

        # message IN
        session.add(
            Message(
                conversation_id=conv.id,
                direction="in",
                text=text,
                raw=raw,
            )
        )
        session.commit()

        # load/create state row
        st = session.get(ConversationState, conv.id)
        if not st:
            st = ConversationState(conversation_id=conv.id, tenant_id=tenant_id, stage="NEW", state={})
            session.add(st)
            session.commit()
            session.refresh(st)

        # advance state machine
        new_stage, new_state, reply = next_step(st.stage, dict(st.state or {}), text)

        # update state
        st.stage = new_stage
        st.state = new_state
        session.add(st)
        session.commit()

        # message OUT
        session.add(
            Message(
                conversation_id=conv.id,
                direction="out",
                text=reply,
                raw={"source": "bot", "mode": "rules", "stage": new_stage},
            )
        )
        session.commit()

        return str(conv.id), reply


def process_payload(payload: dict):
    # ignorar jobs basura
    if not isinstance(payload, dict) or not payload.get("wa_id") or not payload.get("text"):
        print("[WORKER] Ignored payload (missing wa_id/text):", payload)
        return {"ok": False, "ignored": True}

    print("[WORKER] got payload:", payload)
    conv_id, reply = save_incoming_and_reply(payload)
    print("[WORKER] saved incoming. conv_id:", conv_id)
    print("[WORKER] reply:", reply)
    return {"ok": True, "conversation_id": conv_id, "reply": reply}

def handle_incoming(payload: Dict[str, Any]):
    return process_payload(payload)
