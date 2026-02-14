from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
<<<<<<< HEAD
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

# Alias used by background/scheduler.py
async_session = SessionLocal
=======
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
>>>>>>> main
