from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.itinerary import Itinerary


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be blank.")
        return value


class ChatTripContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    destination_id: str | None = Field(
        default=None, alias="destinationId", max_length=64
    )
    title: str | None = Field(default=None, max_length=120)
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    traveler_type: str | None = Field(
        default=None, alias="travelerType", max_length=40
    )
    traveler_count: int | None = Field(default=None, alias="travelerCount", ge=1, le=20)
    budget: int | None = Field(default=None, gt=0)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: str | None = Field(default=None, max_length=40)
    transport: str | None = Field(default=None, max_length=80)
    accommodation: str | None = Field(default=None, max_length=160)
    dietary_needs: str | None = Field(
        default=None, alias="dietaryNeeds", max_length=500
    )
    accessibility_needs: str | None = Field(
        default=None, alias="accessibilityNeeds", max_length=500
    )
    must_visit: list[str] = Field(default_factory=list, alias="mustVisit", max_length=30)
    instructions: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_dates(self) -> "ChatTripContext":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("endDate must be on or after startDate.")
        return self


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)
    context: ChatTripContext | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank.")
        return value


class ChatActivityDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=160)
    time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    duration_minutes: int = Field(alias="durationMinutes", ge=1, le=720)
    category: str = Field(min_length=1, max_length=60)


class ChatDayDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    activities: list[ChatActivityDraft] = Field(min_length=3, max_length=3)


class ChatItineraryDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str = Field(min_length=1, max_length=120)
    destination_id: str = Field(alias="destinationId", min_length=1, max_length=64)
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    traveler_type: str = Field(alias="travelerType", min_length=1, max_length=40)
    traveler_count: int = Field(alias="travelerCount", ge=1, le=20)
    budget: int = Field(ge=1)
    interests: list[str] = Field(min_length=1, max_length=12)
    pace: str = Field(min_length=1, max_length=40)
    transport: str = Field(default="Public transit", max_length=80)
    accommodation: str = Field(default="", max_length=160)
    dietary_needs: str = Field(default="", alias="dietaryNeeds", max_length=500)
    accessibility_needs: str = Field(
        default="", alias="accessibilityNeeds", max_length=500
    )
    must_visit: list[str] = Field(default_factory=list, alias="mustVisit", max_length=30)
    instructions: str = Field(default="", max_length=1000)
    days: list[ChatDayDraft] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_days(self) -> "ChatItineraryDraft":
        trip_days = (self.end_date - self.start_date).days + 1
        if not 1 <= trip_days <= 30:
            raise ValueError("Itinerary dates must span between 1 and 30 days.")
        expected_dates = [
            self.start_date + timedelta(days=day_number)
            for day_number in range(trip_days)
        ]
        if [day.date for day in self.days] != expected_dates:
            raise ValueError("Itinerary days must match the requested dates.")
        return self


class ChatCompletion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reply: str = Field(min_length=1, max_length=4000)
    itinerary: ChatItineraryDraft | None = None


class ChatProviderPart(BaseModel):
    text: str = Field(min_length=1)


class ChatProviderContent(BaseModel):
    parts: list[ChatProviderPart] = Field(min_length=1)


class ChatProviderCandidate(BaseModel):
    content: ChatProviderContent


class ChatProviderResponse(BaseModel):
    candidates: list[ChatProviderCandidate] = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    itinerary: Itinerary | None = None
