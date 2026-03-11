import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.base import Base
# Import all models to ensure they are registered with Base.metadata
from app.models.user import User, UserProfile, OTPCode
from app.models.task import Course, Task, TaskLog, ReflexionLog
from app.models.schedule import FixedSlot
from app.models.sync import CalendarSyncState

async def drop_all():
    print(f"Dropping all tables on database: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    print("Tables dropped successfully.")

if __name__ == "__main__":
    asyncio.run(drop_all())
