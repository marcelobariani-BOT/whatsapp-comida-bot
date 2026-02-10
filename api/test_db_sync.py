import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Tenant, Conversation, Message

def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_engine(url, pool_pre_ping=True)

    with Session(engine) as session:
        tenant_id = "demo"
        t = session.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if not t:
            t = Tenant(id=tenant_id, name="Demo")
            session.add(t)
            session.commit()

        wa_id = "5491100000000"
        conv = session.scalar(select(Conversation).where(Conversation.tenant_id == tenant_id, Conversation.wa_id == wa_id))
        if not conv:
            conv = Conversation(tenant_id=tenant_id, wa_id=wa_id, status="new")
            session.add(conv)
            session.commit()
            session.refresh(conv)

        session.add_all([
            Message(conversation_id=conv.id, direction="in", text="hola", raw={"test": True}),
            Message(conversation_id=conv.id, direction="out", text="menu: 1) empanadas", raw={"test": True}),
        ])
        session.commit()

        print("OK conv_id:", conv.id)

if __name__ == "__main__":
    main()
