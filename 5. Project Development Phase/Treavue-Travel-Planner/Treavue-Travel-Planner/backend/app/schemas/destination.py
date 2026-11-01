from pydantic import BaseModel, ConfigDict, Field


class Destination(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    country: str
    region: str
    description: str
    image: str
    interests: list[str]
    suggested_days: int = Field(alias="suggestedDays", ge=1)
    budget_per_day_inr: int = Field(alias="budgetPerDayINR", ge=0)
    attractions: list[str]
    cuisine: str
    tips: str
