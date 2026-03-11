import pytest
from app.core.config import settings
def test_print_db_url():
    print(f"\nDB URL: {settings.DATABASE_URL}")
