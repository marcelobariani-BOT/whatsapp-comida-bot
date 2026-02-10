import asyncio
from db.session import AsyncSessionLocal
from db.models import Tenant, Conversation, Message
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # tenant
        tenant_id = "demo"
        res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        t = res.scalar_one_or_none()
        if not t:
            t = Tenant(id=tenant_id, name="Demo")
            session.add(t)
            await session.commit()

        # conversation
        wa_id = "5491100000000"
        res = await session.execute(
            select(Conversation).where(Conversation.tenant_id == tenant_id, Conversation.wa_id == wa_id)
        )
        conv = res.scalar_one_or_none()
        if not conv:
            conv = Conversation(tenant_id=tenant_id, wa_id=wa_id, status="new")
            session.add(conv)
            await session.commit()
            await session.refresh(conv)

        # messages
        m1 = Message(conversation_id=conv.id, direction="in", text="hola", raw={"test": True})
        m2 = Message(conversation_id=conv.id, direction="out", text="menu: 1) empanadas", raw={"test": True})
        session.add_all([m1, m2])
        await session.commit()

        print("OK conv_id:", conv.id)

if __name__ == "__main__":
    asyncio.run(main())
