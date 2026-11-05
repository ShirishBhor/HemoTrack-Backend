"""
Common reusable Pydantic schemas.
"""

from pydantic import BaseModel, Field


class StatusUpdate(BaseModel):
    """Schema for toggling or updating the active status of an entity."""

    is_active: bool = Field(
        ...,
        description="Target active status (true to activate/reactivate, false to deactivate)",
    )

