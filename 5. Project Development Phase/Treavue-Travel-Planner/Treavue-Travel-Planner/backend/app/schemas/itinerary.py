from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class GenerateItineraryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    destination_id: str = Field(alias="destinationId", min_length=1, max_length=64)
    title: str = Field(default="", max_length=120)
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    traveler_type: str = Field(default="Solo", alias="travelerType", max_length=40)
    traveler_count: int = Field(default=1, alias="travelerCount", ge=1, le=20)
    budget: int | None = Field(default=None, gt=0)
    interests: list[str] = Field(default_factory=list)
    pace: str = Field(default="Balanced", max_length=40)
    transport: str = Field(default="Public transit", max_length=80)
    accommodation: str = Field(default="", max_length=160)
    dietary_needs: str = Field(default="", alias="dietaryNeeds", max_length=500)
    accessibility_needs: str = Field(
        default="", alias="accessibilityNeeds", max_length=500
    )
    must_visit: list[str] = Field(default_factory=list, alias="mustVisit")
    instructions: str = Field(default="", max_length=1000)


class Activity(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    description: str
    location: str
    time: str
    duration_minutes: int = Field(alias="durationMinutes", ge=1)
    category: str
    cost: int = Field(ge=0)
    currency: str
    notes: str
    fixed: bool


class ItineraryDay(BaseModel):
    id: str
    date: date
    activities: list[Activity]


class Itinerary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    destination_id: str = Field(alias="destinationId")
    stops: list[str]
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    traveler_type: str = Field(alias="travelerType")
    traveler_count: int = Field(alias="travelerCount")
    budget: int
    currency: str
    interests: list[str]
    pace: str
    transport: str
    accommodation: str
    dietary_needs: str = Field(alias="dietaryNeeds")
    accessibility_needs: str = Field(alias="accessibilityNeeds")
    must_visit: list[str] = Field(alias="mustVisit")
    excluded_activities: list[str] = Field(alias="excludedActivities")
    instructions: str
    status: str
    days: list[ItineraryDay]
    notes: str
    created_at: date = Field(alias="createdAt")
