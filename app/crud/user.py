from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.schemas import UserCreate


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate, hashed_password: str) -> User:
    count_query = select(func.count(User.id))
    count_result = await db.execute(count_query)
    total_users = count_result.scalar() or 0

    assigned_role = "admin" if total_users == 0 else "user"

    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        role=assigned_role
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def promote_user_to_admin(db: AsyncSession, user_id: int) -> User | None:
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user:
        user.role = "admin"
        await db.commit()
        await db.refresh(user)
    return user
