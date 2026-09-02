import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.enums import RoleEnum
from app.core.security import get_password_hash


async def seed():
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == "admin@example.com")
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            print("User admin@example.com already exists!")
            return

        user = User(
            email="admin@example.com",
            hashed_password=get_password_hash("Admin123456!"),
            full_name="Admin User",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        org = Organization(
            name="Demo Store Inc",
            slug="demo-store-inc",
        )
        db.add(org)
        await db.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=RoleEnum.OWNER,
        )
        db.add(member)

        await db.commit()
        print("Demo account created successfully:")
        print("  Email:    admin@example.com")
        print("  Password: Admin123456!")
        print("  Org:      Demo Store Inc (Role: OWNER)")


if __name__ == "__main__":
    asyncio.run(seed())
