from fastapi import APIRouter, HTTPException

from app.data.destinations import DESTINATIONS_BY_ID
from app.schemas.destination import Destination

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("", response_model=list[Destination], summary="List destinations")
def list_destinations() -> list[Destination]:
    return list(DESTINATIONS_BY_ID.values())


@router.get(
    "/{destination_id}",
    response_model=Destination,
    summary="Get a destination",
)
def get_destination(destination_id: str) -> Destination:
    destination = DESTINATIONS_BY_ID.get(destination_id)
    if destination is None:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{destination_id}' was not found.",
        )
    return destination
