"""Tests for the /health endpoint and basic app startup."""

import pytest
from httpx import AsyncClient


class TestHealth:
    """Health-check / smoke tests."""

    async def test_health_endpoint_returns_200(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_response_body(self, client: AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "service" in data

    async def test_openapi_schema_accessible(self, client: AsyncClient):
        resp = await client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
