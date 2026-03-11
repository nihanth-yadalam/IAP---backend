"""
Legacy router — kept for backward compatibility.
The canonical router is app.api.v1.router (mounted by app/main.py).
"""
from app.api.v1.router import api_router  # noqa: F401 — re-export
