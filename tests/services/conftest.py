"""
Conftest for services tests — override the root conftest to avoid SQLite JSONB issues.
Pure function tests don't need a database.
"""
