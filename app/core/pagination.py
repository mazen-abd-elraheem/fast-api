"""
Sanaie Platform — Pagination Utilities
Shared pagination helpers to enforce limits across all API endpoints.
"""
from fastapi import Query


def PaginationParams(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=50, description="Max items to return (1-50)"),
):
    """
    FastAPI dependency for consistent pagination across all endpoints.
    Enforces max 50 items per page.
    """
    return {"skip": skip, "limit": min(limit, 50)}
