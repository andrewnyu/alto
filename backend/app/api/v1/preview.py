from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.models.preview import GeocodeRequest, GeocodeResponse, PreviewRequest, PreviewResponse
from app.services.maps_service import MapsService
from app.services.orchestrator import PreviewOrchestrator

router = APIRouter(prefix="/api/v1", tags=["preview"])
logger = logging.getLogger(__name__)


@router.post("/preview", response_model=PreviewResponse)
async def generate_preview(payload: PreviewRequest, request: Request) -> PreviewResponse:
    orchestrator: PreviewOrchestrator | None = getattr(request.app.state, "preview_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview engine is not initialized",
        )

    try:
        return await orchestrator.generate_preview(payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Preview synthesis failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Preview synthesis failed",
        ) from None


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(payload: GeocodeRequest, request: Request) -> GeocodeResponse:
    maps_service: MapsService | None = getattr(request.app.state, "maps_service", None)
    if maps_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoder is not initialized",
        )

    try:
        formatted, lat, lng = await maps_service.geocode_address(payload.address)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No geocoding result for address",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Maps key is not configured",
        ) from None
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Geocoding failed: {str(exc)[:280]}",
        ) from None
    except Exception:
        logger.exception("Geocoding failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding failed",
        ) from None

    return GeocodeResponse(
        address=payload.address,
        formatted_address=formatted,
        lat=lat,
        lng=lng,
        provider="googlemaps",
    )
