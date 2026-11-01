from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_destinations_matches_frontend_contract() -> None:
    response = client.get("/api/destinations")

    assert response.status_code == 200
    destinations = response.json()
    assert len(destinations) == 6
    assert destinations[0]["id"] == "kyoto"
    assert destinations[0]["suggestedDays"] == 5
    assert destinations[0]["budgetPerDayINR"] == 9800


def test_get_destination_returns_not_found_for_unknown_id() -> None:
    response = client.get("/api/destinations/not-a-destination")

    assert response.status_code == 404
    assert response.json()["detail"] == "Destination 'not-a-destination' was not found."


def test_get_destination_returns_full_destination_data() -> None:
    response = client.get("/api/destinations/kyoto")

    assert response.status_code == 200
    assert response.json()["name"] == "Kyoto"
    assert response.json()["attractions"][0] == "Fushimi Inari Shrine"


def test_generate_itinerary_returns_days_for_requested_dates() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "title": "Kyoto weekend",
            "startDate": "2026-11-01",
            "endDate": "2026-11-03",
            "travelerType": "Couple",
            "travelerCount": 2,
            "interests": ["Culture", "Food"],
            "mustVisit": ["Fushimi Inari Shrine"],
        },
    )

    assert response.status_code == 200
    itinerary = response.json()
    assert itinerary["destinationId"] == "kyoto"
    assert itinerary["startDate"] == "2026-11-01"
    assert itinerary["endDate"] == "2026-11-03"
    assert itinerary["budget"] == 9800 * 3
    assert len(itinerary["days"]) == 3
    assert [day["date"] for day in itinerary["days"]] == [
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
    ]
    assert len(itinerary["days"][0]["activities"]) == 3


def test_generate_itinerary_uses_destination_specific_schedules() -> None:
    expected_attractions = {
        "kyoto": "Fushimi Inari Shrine",
        "lisbon": "Alfama",
        "jaipur": "Amber Fort",
        "bali": "Tegallalang Rice Terraces",
        "istanbul": "Hagia Sophia",
        "marrakech": "Jardin Majorelle",
    }

    for destination_id, expected_attraction in expected_attractions.items():
        response = client.post(
            "/api/itineraries/generate",
            json={
                "destinationId": destination_id,
                "startDate": "2026-11-01",
                "endDate": "2026-11-01",
            },
        )

        assert response.status_code == 200
        itinerary = response.json()
        activities = itinerary["days"][0]["activities"]
        assert itinerary["days"][0]["date"] == "2026-11-01"
        assert len(activities) == 3
        assert any(expected_attraction in activity["title"] for activity in activities)
        assert "unverified examples, not live prices" in itinerary["notes"]


def test_generate_itinerary_rotates_schedules_for_each_requested_day() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "startDate": "2026-11-01",
            "endDate": "2026-11-04",
        },
    )

    assert response.status_code == 200
    days = response.json()["days"]
    assert [day["date"] for day in days] == [
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]
    assert all(len(day["activities"]) == 3 for day in days)
    day_titles = [
        [activity["title"] for activity in day["activities"]]
        for day in days
    ]
    assert day_titles[0] != day_titles[1]
    assert day_titles[0] == day_titles[3]


def test_generate_itinerary_uses_interests_budget_and_pace() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "startDate": "2026-11-01",
            "endDate": "2026-11-03",
            "travelerCount": 1,
            "budget": 100,
            "interests": ["Nature"],
            "pace": "Slow",
        },
    )

    assert response.status_code == 200
    itinerary = response.json()
    assert all(len(day["activities"]) == 2 for day in itinerary["days"])
    assert any(
        activity["category"] == "Nature"
        for day in itinerary["days"]
        for activity in day["activities"]
    )
    assert itinerary["budget"] == 100


def test_generate_itinerary_uses_low_budget_to_prefer_lower_sample_amounts() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "lisbon",
            "startDate": "2026-11-01",
            "endDate": "2026-11-01",
            "budget": 500,
        },
    )

    assert response.status_code == 200
    activities = response.json()["days"][0]["activities"]
    assert activities[0]["title"] == "Belém Tower riverside visit"
    assert sum(activity["cost"] for activity in activities) == 900
    assert "Itemized activity amounts by category: Food: INR 900" in response.json()["notes"]
    assert "Day 1 neighborhood sequence: Belém" in response.json()["notes"]


def test_generate_itinerary_prioritizes_known_must_visits_and_notes_constraints() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "jaipur",
            "startDate": "2026-11-01",
            "endDate": "2026-11-01",
            "interests": ["Architecture"],
            "mustVisit": ["Amber Fort"],
            "transport": "Walking",
            "dietaryNeeds": "Vegetarian",
            "accessibilityNeeds": "Avoid stairs",
            "accommodation": "Step-free guesthouse",
        },
    )

    assert response.status_code == 200
    itinerary = response.json()
    activities = itinerary["days"][0]["activities"]
    assert any("Amber Fort" in activity["title"] for activity in activities)
    assert "Walking transport preference" in itinerary["notes"]
    assert "Dietary needs noted (Vegetarian)" in itinerary["notes"]
    assert "accessibility at stops is not verified" in itinerary["notes"]
    assert "No lodging listings or prices are available" in itinerary["notes"]
    assert all(
        "unverified" in activity["notes"].lower()
        or "not verified" in activity["notes"].lower()
        or "no price data" in activity["notes"].lower()
        for activity in activities
    )


def test_generate_itinerary_reports_unsupported_must_visits_and_non_live_routes() -> None:
    response = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "lisbon",
            "startDate": "2026-11-01",
            "endDate": "2026-11-01",
            "mustVisit": ["A place not in the sample data"],
        },
    )

    assert response.status_code == 200
    assert "Requested stops not included in the selected itinerary" in response.json()["notes"]
    assert "not live route optimization" in response.json()["notes"]


def test_generate_itinerary_validates_input_and_unknown_destination() -> None:
    invalid_dates = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "startDate": "2026-11-03",
            "endDate": "2026-11-01",
        },
    )
    unknown_destination = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "unknown",
            "startDate": "2026-11-01",
            "endDate": "2026-11-03",
        },
    )
    invalid_travelers = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "startDate": "2026-11-01",
            "endDate": "2026-11-03",
            "travelerCount": 0,
        },
    )
    overlong_trip = client.post(
        "/api/itineraries/generate",
        json={
            "destinationId": "kyoto",
            "startDate": "2026-11-01",
            "endDate": "2026-12-01",
        },
    )

    assert invalid_dates.status_code == 422
    assert unknown_destination.status_code == 404
    assert invalid_travelers.status_code == 422
    assert overlong_trip.status_code == 422


def test_api_allows_configured_frontend_origin() -> None:
    response = client.get(
        "/api/destinations",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "http://localhost:5173"
    )
