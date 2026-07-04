"""Supported EVM chain catalog API (M5.0)."""

from fastapi import APIRouter, Depends

from app.schemas.chain import ChainListResponse
from app.services.chain_service import ChainService

router = APIRouter()


def get_chain_service() -> ChainService:
    return ChainService()


@router.get(
    "/chains",
    response_model=ChainListResponse,
    summary="List supported EVM chains",
    description="Return chain metadata for all chains ChainSentinel can scan.",
)
async def list_chains(
    service: ChainService = Depends(get_chain_service),
) -> ChainListResponse:
    return service.list_supported_chains()
