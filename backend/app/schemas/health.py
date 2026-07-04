"""Health check response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Public health probe response for load balancers and monitoring."""

    status: str = Field(
        ...,
        examples=["healthy"],
        description="Current service health state.",
    )
    service: str = Field(
        ...,
        examples=["ChainSentinel API"],
        description="Human-readable service name.",
    )
    version: str = Field(
        ...,
        examples=["0.1.0"],
        description="API semantic version.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "service": "ChainSentinel API",
                    "version": "0.1.0",
                }
            ]
        }
    }
