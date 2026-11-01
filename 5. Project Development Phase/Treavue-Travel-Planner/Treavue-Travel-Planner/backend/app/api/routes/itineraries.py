from datetime import date, timedelta
from math import log1p
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.data.destinations import DESTINATIONS_BY_ID
from app.schemas.itinerary import GenerateItineraryRequest, Itinerary

router = APIRouter(prefix="/itineraries", tags=["itineraries"])

MAX_TRIP_DAYS = 30


def _matches_requested_stop(requested: str, title: str) -> bool:
    requested_name = requested.casefold().strip()
    activity_title = title.casefold().strip()
    return requested_name == activity_title or (
        min(len(requested_name), len(activity_title)) >= 5
        and (requested_name in activity_title or activity_title in requested_name)
    )


ActivitySchedule = tuple[str, str, str, int, str]
DailySchedule = tuple[ActivitySchedule, ActivitySchedule, ActivitySchedule]

ACTIVITY_INTERESTS = {
    "temple": {"culture", "history"},
    "food": {"food"},
    "nature": {"nature", "wellness"},
    "walk": {"nature", "culture"},
    "viewpoint": {"nature", "coast"},
    "history": {"history", "culture"},
    "architecture": {"architecture", "culture", "history"},
    "shopping": {"shopping", "culture"},
    "culture": {"culture"},
}

SCHEDULES: dict[str, tuple[DailySchedule, ...]] = {
    "kyoto": (
        (
            ("Fushimi Inari Shrine", "07:30", "Temple", 0, "Fushimi-ku"),
            ("Nishiki Market lunch", "12:15", "Food", 1200, "Nishiki Market"),
            ("Kiyomizu-dera hillside visit", "15:30", "Temple", 0, "Higashiyama"),
        ),
        (
            ("Arashiyama Bamboo Grove", "08:00", "Nature", 0, "Arashiyama"),
            ("Riverside yudofu lunch", "12:30", "Food", 1800, "Arashiyama"),
            ("Gion neighborhood walk", "16:30", "Walk", 0, "Gion"),
        ),
        (
            ("Kiyomizu-dera morning visit", "08:30", "Temple", 0, "Higashiyama"),
            (
                "Obanzai lunch near Nishiki Market",
                "12:30",
                "Food",
                1500,
                "Central Kyoto",
            ),
            ("Fushimi Inari Shrine evening walk", "16:00", "Temple", 0, "Fushimi-ku"),
        ),
    ),
    "lisbon": (
        (
            ("Alfama morning walk", "09:00", "Walk", 0, "Alfama"),
            ("Petiscos lunch in Graça", "12:30", "Food", 1800, "Graça"),
            (
                "Miradouro da Senhora do Monte at sunset",
                "18:00",
                "Viewpoint",
                0,
                "São Vicente",
            ),
        ),
        (
            ("Belém Tower riverside visit", "09:00", "History", 0, "Belém"),
            ("Pastéis de nata break", "12:00", "Food", 900, "Belém"),
            ("LX Factory late afternoon browse", "16:00", "Culture", 0, "Alcântara"),
        ),
        (
            ("LX Factory morning galleries", "10:00", "Culture", 0, "Alcântara"),
            ("Lunch in Alfama", "13:00", "Food", 1600, "Alfama"),
            ("Belém waterfront stroll", "17:00", "Walk", 0, "Belém"),
        ),
    ),
    "jaipur": (
        (
            ("Amber Fort morning visit", "08:00", "History", 500, "Amer"),
            ("Rajasthani lunch in the old city", "12:30", "Food", 1200, "Jaipur"),
            (
                "Hawa Mahal from the old city lanes",
                "16:00",
                "Architecture",
                200,
                "Badi Choupad",
            ),
        ),
        (
            ("City Palace courtyards", "09:00", "History", 500, "Pink City"),
            ("Lunch near Hawa Mahal", "12:30", "Food", 1400, "Pink City"),
            ("Bapu Bazaar craft walk", "16:00", "Shopping", 0, "Bapu Bazaar"),
        ),
        (
            ("Hawa Mahal morning visit", "08:30", "Architecture", 200, "Badi Choupad"),
            ("Lunch in the Pink City", "12:30", "Food", 1300, "Pink City"),
            ("City Palace afternoon visit", "15:30", "History", 500, "Pink City"),
        ),
    ),
    "bali": (
        (
            ("Tegallalang Rice Terraces", "08:00", "Nature", 300, "Tegallalang"),
            ("Lunch at a Ubud café", "12:30", "Food", 1200, "Ubud"),
            ("Ubud Art Market", "15:30", "Shopping", 0, "Ubud"),
        ),
        (
            ("Campuhan Ridge Walk", "07:30", "Nature", 0, "Campuhan"),
            ("Nasi campur lunch", "12:00", "Food", 1000, "Ubud"),
            ("Goa Gajah afternoon visit", "15:00", "History", 300, "Bedulu"),
        ),
        (
            ("Goa Gajah morning visit", "08:30", "History", 300, "Bedulu"),
            ("Lunch near Ubud Art Market", "12:30", "Food", 1100, "Ubud"),
            ("Campuhan Ridge Walk at golden hour", "16:00", "Nature", 0, "Campuhan"),
        ),
    ),
    "istanbul": (
        (
            ("Hagia Sophia morning visit", "09:00", "History", 0, "Sultanahmet"),
            ("Lunch near the Spice Bazaar", "12:30", "Food", 1500, "Eminönü"),
            ("Spice Bazaar afternoon browse", "15:00", "Shopping", 0, "Eminönü"),
        ),
        (
            ("Galata Tower neighborhood walk", "09:00", "Architecture", 0, "Galata"),
            ("Simit and tea by the Bosphorus", "12:00", "Food", 500, "Karaköy"),
            ("Kadıköy market and waterfront", "16:00", "Culture", 0, "Kadıköy"),
        ),
        (
            ("Spice Bazaar morning visit", "09:30", "Shopping", 0, "Eminönü"),
            ("Meze lunch in Kadıköy", "13:00", "Food", 1800, "Kadıköy"),
            ("Galata Tower at dusk", "17:00", "Viewpoint", 0, "Galata"),
        ),
    ),
    "marrakech": (
        (
            ("Jardin Majorelle morning visit", "09:00", "Nature", 500, "Gueliz"),
            ("Lunch near the medina", "12:30", "Food", 1300, "Medina"),
            ("Medina souks afternoon walk", "15:30", "Shopping", 0, "Medina"),
        ),
        (
            ("Bahia Palace morning visit", "09:00", "History", 300, "Mellah"),
            ("Harira lunch in the medina", "12:30", "Food", 900, "Medina"),
            (
                "Ben Youssef Madrasa afternoon visit",
                "15:00",
                "Architecture",
                300,
                "Medina",
            ),
        ),
        (
            (
                "Ben Youssef Madrasa morning visit",
                "09:00",
                "Architecture",
                300,
                "Medina",
            ),
            ("Tajine lunch in the old city", "12:30", "Food", 1400, "Medina"),
            ("Bahia Palace gardens and courtyards", "15:30", "History", 300, "Mellah"),
        ),
    ),
}


def _make_itinerary(request: GenerateItineraryRequest, trip_days: int) -> Itinerary:
    destination = DESTINATIONS_BY_ID[request.destination_id]
    destination_schedules = SCHEDULES[destination.id]
    days = []
    normalized_interests = {interest.strip().casefold() for interest in request.interests}
    remaining_must_visits = [place.strip() for place in request.must_visit if place.strip()]
    pace = request.pace.strip().casefold()
    stops_per_day = 2 if pace == "slow" else 3
    daily_budget_guide = (
        request.budget / trip_days / request.traveler_count
        if request.budget is not None
        else destination.budget_per_day_inr
    )
    schedule_uses = [0] * len(destination_schedules)

    for day_number in range(trip_days):
        current_date = request.start_date + timedelta(days=day_number)
        def schedule_score(schedule_number: int) -> tuple[float, int]:
            schedule = sorted(
                destination_schedules[schedule_number],
                key=lambda activity: activity[1],
            )[:stops_per_day]
            interest_score = sum(
                len(
                    ACTIVITY_INTERESTS.get(category.casefold(), set())
                    & normalized_interests
                )
                for _, _, category, _, _ in schedule
            )
            must_visit_score = sum(
                100
                for place in remaining_must_visits
                if any(
                    _matches_requested_stop(place, title)
                    for title, _, _, _, _ in schedule
                )
            )
            sample_amount = sum(cost for _, _, _, cost, _ in schedule)
            budget_penalty = (
                log1p(sample_amount / max(daily_budget_guide, 1)) * 0.75
                if request.budget is not None
                else 0
            )
            variety_penalty = schedule_uses[schedule_number] * 2
            return (
                must_visit_score + interest_score - budget_penalty - variety_penalty,
                -schedule_number,
            )

        schedule_number = max(
            range(len(destination_schedules)),
            key=schedule_score,
        )
        schedule_uses[schedule_number] += 1
        schedule = destination_schedules[schedule_number]
        selected_activities = sorted(schedule, key=lambda activity: activity[1])[
            :stops_per_day
        ]

        for title, _, _, _, _ in selected_activities:
            remaining_must_visits = [
                place
                for place in remaining_must_visits
                if not _matches_requested_stop(place, title)
            ]

        activities = []
        for activity_number, (title, time, category, cost, location) in enumerate(
            selected_activities
        ):
            is_dining = category.casefold() == "food"
            activity_notes = (
                "Dietary suitability is not verified; contact the venue directly."
                if is_dining and request.dietary_needs
                else "Unverified sample estimate; confirm the amount locally."
                if cost > 0
                else "No price data is available for this stop."
            )
            activities.append(
                {
                    "id": f"{day_number + 1}-{activity_number}",
                    "title": title,
                    "time": time,
                    "category": category,
                    "cost": cost,
                    "location": location,
                    "durationMinutes": 90,
                    "currency": "INR",
                    "description": f"A considered stop for {title.lower()}.",
                    "notes": activity_notes,
                    "fixed": False,
                }
            )
        days.append(
            {
                "id": f"day-{day_number + 1}",
                "date": current_date,
                "activities": activities,
            }
        )

    activity_costs_by_category: dict[str, int] = {}
    for itinerary_day in days:
        for activity in itinerary_day["activities"]:
            if activity["cost"] > 0:
                category = activity["category"]
                activity_costs_by_category[category] = (
                    activity_costs_by_category.get(category, 0) + activity["cost"]
                )

    planner_notes = [
        "Deterministic sample itinerary based on Treavue's destination notes. "
        "Activity amounts are unverified examples, not live prices.",
        f"Destination guidance: {destination.tips}",
        (
            f"Dining inspiration from the destination guide: {destination.cuisine}. "
            "These are cuisine ideas, not verified restaurant recommendations."
        ),
        (
            f"Route order follows the listed neighborhood labels and your "
            f"{request.transport or 'unspecified'} transport preference; it is "
            "not live route optimization or a travel-time estimate."
        ),
    ]
    if activity_costs_by_category:
        itemized_costs = "; ".join(
            f"{category}: INR {amount:,} (unverified sample amount)"
            for category, amount in sorted(activity_costs_by_category.items())
        )
        planner_notes.append(
            f"Itemized activity amounts by category: {itemized_costs}. "
            "This excludes accommodation, meals without sample amounts, and "
            "transport."
        )
    else:
        planner_notes.append(
            "No itemized activity prices are available in the sample data; "
            "accommodation, dining, and transport costs are not estimated."
        )
    for day_number, itinerary_day in enumerate(days, start=1):
        locations = list(
            dict.fromkeys(
                activity["location"]
                for activity in itinerary_day["activities"]
                if activity["location"]
            )
        )
        if locations:
            planner_notes.append(
                f"Day {day_number} neighborhood sequence: {' → '.join(locations)}. "
                "Use this as a grouping suggestion only; check a current map for "
                "routes and travel times."
            )
    if request.dietary_needs:
        planner_notes.append(
            f"Dietary needs noted ({request.dietary_needs}); dining suggestions "
            "are not verified for suitability."
        )
    if request.accessibility_needs:
        planner_notes.append(
            f"Accessibility needs noted ({request.accessibility_needs}); "
            "accessibility at stops is not verified."
        )
    if request.accommodation:
        planner_notes.append(
            f"Accommodation preference recorded: {request.accommodation}. "
            "No lodging listings or prices are available in the destination data."
        )
    if remaining_must_visits:
        planner_notes.append(
            "Requested stops not included in the selected itinerary "
            "(check for a matching sample activity): "
            + ", ".join(remaining_must_visits)
            + "."
        )

    return Itinerary(
        id=f"trip-{uuid4()}",
        title=request.title or f"{destination.name} getaway",
        destination_id=destination.id,
        stops=[destination.id],
        start_date=request.start_date,
        end_date=request.end_date,
        traveler_type=request.traveler_type,
        traveler_count=request.traveler_count,
        budget=request.budget or destination.budget_per_day_inr * trip_days,
        currency="INR",
        interests=request.interests,
        pace=request.pace,
        transport=request.transport,
        accommodation=request.accommodation,
        dietary_needs=request.dietary_needs,
        accessibility_needs=request.accessibility_needs,
        must_visit=request.must_visit,
        excluded_activities=[],
        instructions=request.instructions,
        status="draft",
        days=days,
        notes=" ".join(planner_notes),
        created_at=date.today(),
    )


@router.post(
    "/generate",
    response_model=Itinerary,
    summary="Generate a sample itinerary",
)
def generate_itinerary(request: GenerateItineraryRequest) -> Itinerary:
    if request.destination_id not in DESTINATIONS_BY_ID:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{request.destination_id}' was not found.",
        )
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=422,
            detail="endDate must be on or after startDate.",
        )

    trip_days = (request.end_date - request.start_date).days + 1
    if trip_days > MAX_TRIP_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Trips cannot exceed {MAX_TRIP_DAYS} days.",
        )

    return _make_itinerary(request, trip_days)
