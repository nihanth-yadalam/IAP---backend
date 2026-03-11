import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def reset_types():
    # Construct async URL from settings or hardcoded (easier here to trust settings)
    # But need to setup env if not loaded.
    # We can just use the URL string if we know it or import settings.
    # settings.DATABASE_URL
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Dropping types...")
        await conn.execute(text("DROP TYPE IF EXISTS prioritylevel CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS taskcategory CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS taskstatus CASCADE"))
        # Also maybe drop tables to be sure? 
        # But downgrade base should have dropped tables.
        # Let's drop tables just in case 'downgrade base' failed silently or partially?
        # No, 'downgrade base' output was success.
        
    print("Types dropped.")
    await engine.dispose()

if __name__ == "__main__":
    import sys
    sys.path.append(os.getcwd())
    asyncio.run(reset_types())
