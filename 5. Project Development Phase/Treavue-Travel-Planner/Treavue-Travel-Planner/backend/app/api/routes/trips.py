import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from supabase import Client

from app.core.auth import AuthenticatedUser, require_authenticated_user
from app.core.supabase import get_supabase_client
from app.schemas.itinerary import Itinerary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips", tags=["trips"])


def _client_or_503(access_token: str) -> Client:
    try:
        client = get_supabase_client(access_token)
    except Exception as error:
        logger.error("Supabase client initialization failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trip storage is unavailable. Check the backend Supabase configuration.",
        ) from None
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trip storage is not configured. Trips remain available in this browser.",
        )
    return client


def _trip_columns(trip: Itinerary, user_id: str) -> dict[str, Any]:
    trip_data = trip.model_dump(mode="json", by_alias=True)
    return {
        "id": trip.id,
        "name": trip.title,
        "destination": trip.destination_id,
        "trip_data": trip_data,
        "user_id": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _trip_from_row(row: dict[str, Any]) -> Itinerary:
    try:
        return Itinerary.model_validate(row["trip_data"])
    except (KeyError, TypeError, ValidationError) as error:
        logger.error("Supabase returned an invalid trip record (%s)", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Trip storage returned an invalid record.",
        ) from None


def _safe_provider_code(error: Exception) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, (str, int)) and not isinstance(code, bool):
        candidate = str(code)
        if re.fullmatch(r"\d{3,5}", candidate):
            return candidate
    return "unavailable"


def _handle_storage_error(error: Exception, operation: str) -> None:
    logger.error(
        "Supabase trip %s failed (%s; provider_code=%s)",
        operation,
        type(error).__name__,
        _safe_provider_code(error),
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Trip storage could not complete the request.",
    ) from None


@router.get("", response_model=list[Itinerary], summary="List saved trips")
def list_trips(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> list[Itinerary]:
    client = _client_or_503(current_user.access_token)
    try:
        response = (
            client.table("trips")
            .select("id, name, destination, trip_data, created_at, updated_at")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as error:
        _handle_storage_error(error, "list")
    return [_trip_from_row(row) for row in (response.data or [])]


@router.get(
    "/{trip_id}",
    response_model=Itinerary,
    summary="Get a saved trip",
)
def get_trip(
    trip_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> Itinerary:
    client = _client_or_503(current_user.access_token)
    try:
        response = (
            client.table("trips")
            .select("id, name, destination, trip_data, created_at, updated_at")
            .eq("id", trip_id)
            .eq("user_id", current_user.id)
            .limit(1)
            .execute()
        )
    except Exception as error:
        _handle_storage_error(error, "get")
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    return _trip_from_row(response.data[0])


@router.post(
    "",
    response_model=Itinerary,
    summary="Create or save a trip",
)
def save_trip(
    trip: Itinerary,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> Itinerary:
    client = _client_or_503(current_user.access_token)
    try:
        client.table("trips").insert(_trip_columns(trip, current_user.id)).execute()
    except Exception as error:
        if getattr(error, "code", None) == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A trip with this ID already exists in your account.",
            ) from None
        _handle_storage_error(error, "insert")
    return trip


@router.put(
    "/{trip_id}",
    response_model=Itinerary,
    summary="Update a saved trip",
)
def update_trip(
    trip_id: str,
    trip: Itinerary,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> Itinerary:
    if trip.id != trip_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The trip ID in the path must match the trip ID in the body.",
        )

    client = _client_or_503(current_user.access_token)
    try:
        response = (
            client.table("trips")
            .update(_trip_columns(trip, current_user.id))
            .eq("id", trip_id)
            .eq("user_id", current_user.id)
            .select("id, name, destination, trip_data, created_at, updated_at")
            .execute()
        )
    except Exception as error:
        _handle_storage_error(error, "update")
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    return _trip_from_row(response.data[0])


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved trip",
)
def delete_trip(
    trip_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> None:
    client = _client_or_503(current_user.access_token)
    try:
        response = (
            client.table("trips")
            .delete()
            .eq("id", trip_id)
            .eq("user_id", current_user.id)
            .select("id")
            .execute()
        )
    except Exception as error:
        _handle_storage_error(error, "delete")
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
