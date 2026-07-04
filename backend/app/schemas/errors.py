"""Structured API error response schemas."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope returned by global exception handlers."""

    detail: str = Field(..., description="Human-readable error message.")
    error_code: str = Field(..., description="Machine-readable error category.")
