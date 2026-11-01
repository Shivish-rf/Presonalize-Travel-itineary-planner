from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.core import auth as auth_core
from app.core import supabase as supabase_core
from app.api.routes import trips as trips_route
from app.main import app

client = TestClient(app)


def test_auth_client_uses_the_low_privilege_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_args: list[tuple[str, str]] = []
    fake_client = FakeSupabase()
    monkeypatch.setattr(supabase_core.settings, "supabase_url", "https://project.test")
    monkeypatch.setattr(
        supabase_core.settings, "supabase_auth_api_key", "publishable-key"
    )
    monkeypatch.setattr(
        supabase_core,
        "_create_auth_client",
        lambda url, api_key: client_args.append((url, api_key)) or fake_client,
    )

    result = supabase_core.get_supabase_auth_client()

    assert result is fake_client
    assert client_args == [("https://project.test", "publishable-key")]


def test_trip_client_uses_verified_user_token_and_public_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_args: list[tuple[str, str, Any]] = []
    fake_client = FakeSupabase()
    monkeypatch.setattr(supabase_core.settings, "supabase_url", "https://project.test")
    monkeypatch.setattr(
        supabase_core.settings, "supabase_auth_api_key", "publishable-key"
    )
    monkeypatch.setattr(
        supabase_core,
        "create_client",
        lambda url, api_key, options: (
            client_args.append((url, api_key, options)) or fake_client
        ),
    )

    result = supabase_core.get_supabase_client("verified-user-token")

    assert result is fake_client
    assert len(client_args) == 1
    url, api_key, options = client_args[0]
    assert url == "https://project.test"
    assert api_key == "publishable-key"
    assert options.headers["Authorization"] == "Bearer verified-user-token"
    assert options.auto_refresh_token is False
    assert options.persist_session is False


def trip_payload() -> dict[str, Any]:
    return {
        "id": "trip-test-1",
        "title": "Kyoto weekend",
        "destinationId": "kyoto",
        "stops": ["kyoto"],
        "startDate": "2026-11-01",
        "endDate": "2026-11-02",
        "travelerType": "Couple",
        "travelerCount": 2,
        "budget": 12000,
        "currency": "INR",
        "interests": ["Culture", "Food"],
        "pace": "Balanced",
        "transport": "Public transit",
        "accommodation": "",
        "dietaryNeeds": "",
        "accessibilityNeeds": "",
        "mustVisit": ["Fushimi Inari Shrine"],
        "excludedActivities": [],
        "instructions": "",
        "status": "draft",
        "days": [
            {
                "id": "day-1",
                "date": "2026-11-01",
                "activities": [
                    {
                        "id": "activity-1",
                        "title": "Fushimi Inari Shrine",
                        "description": "Visit the shrine.",
                        "location": "Fushimi-ku",
                        "time": "08:00",
                        "durationMinutes": 90,
                        "category": "Temple",
                        "cost": 0,
                        "currency": "INR",
                        "notes": "",
                        "fixed": False,
                    }
                ],
            }
        ],
        "notes": "",
        "createdAt": "2026-10-21",
    }


class FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.action = "select"
        self.values: dict[str, Any] = {}
        self.filters: dict[str, str] = {}

    def select(self, _columns: str) -> "FakeQuery":
        return self

    def order(self, _column: str, desc: bool = False) -> "FakeQuery":
        return self

    def limit(self, _limit: int) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters[column] = value
        return self

    def insert(self, values: dict[str, Any]) -> "FakeQuery":
        self.action = "insert"
        self.values = values
        return self

    def update(self, values: dict[str, Any]) -> "FakeQuery":
        self.action = "update"
        self.values = values
        return self

    def delete(self) -> "FakeQuery":
        self.action = "delete"
        return self

    def execute(self) -> SimpleNamespace:
        matching = [
            row for row in self.rows
            if all(row.get(column) == value for column, value in self.filters.items())
        ]
        if self.action == "insert":
            self.rows.append(deepcopy(self.values))
            return SimpleNamespace(data=[deepcopy(self.values)])
        if self.action == "update":
            for row in matching:
                row.update(deepcopy(self.values))
            return SimpleNamespace(data=deepcopy(matching))
        if self.action == "delete":
            self.rows[:] = [row for row in self.rows if row not in matching]
            return SimpleNamespace(data=deepcopy(matching))
        return SimpleNamespace(data=deepcopy(matching))


class FakeSupabase:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.auth = SimpleNamespace(get_user=self.get_user)

    def table(self, _name: str) -> FakeQuery:
        return FakeQuery(self.rows)

    @staticmethod
    def get_user(token: str) -> SimpleNamespace:
        if token == "valid-user-1":
            return SimpleNamespace(
                user=SimpleNamespace(id="user-1", email="one@example.test")
            )
        if token == "valid-user-2":
            return SimpleNamespace(
                user=SimpleNamespace(id="user-2", email="two@example.test")
            )
        raise ValueError("invalid token")


AUTH_USER_1 = {"Authorization": "Bearer valid-user-1"}
AUTH_USER_2 = {"Authorization": "Bearer valid-user-2"}

@pytest.fixture
def supabase_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabase:
    fake_client = FakeSupabase()
    monkeypatch.setattr(
        trips_route, "get_supabase_client", lambda _access_token: fake_client
    )
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: fake_client)
    return fake_client


def test_trip_crud_round_trips_full_trip_and_database_columns(
    supabase_client: FakeSupabase,
) -> None:
    payload = trip_payload()
    create = client.post(
        "/api/trips",
        json={**payload, "user_id": "user-2"},
        headers=AUTH_USER_1,
    )
    assert create.status_code == 200
    assert create.json() == payload
    assert supabase_client.rows[0]["name"] == payload["title"]
    assert supabase_client.rows[0]["destination"] == payload["destinationId"]
    assert supabase_client.rows[0]["trip_data"] == payload
    assert supabase_client.rows[0]["user_id"] == "user-1"

    listing = client.get("/api/trips", headers=AUTH_USER_1)
    assert listing.status_code == 200
    assert listing.json() == [payload]

    get_response = client.get("/api/trips/trip-test-1", headers=AUTH_USER_1)
    assert get_response.status_code == 200
    assert get_response.json() == payload

    updated = {**payload, "title": "Kyoto trip renamed"}
    update_response = client.put(
        "/api/trips/trip-test-1",
        json=updated,
        headers=AUTH_USER_1,
    )
    assert update_response.status_code == 200
    assert update_response.json() == updated
    assert supabase_client.rows[0]["name"] == "Kyoto trip renamed"

    delete_response = client.delete("/api/trips/trip-test-1", headers=AUTH_USER_1)
    assert delete_response.status_code == 204
    assert supabase_client.rows == []


def test_trip_endpoints_return_not_found_for_missing_records(
    supabase_client: FakeSupabase,
) -> None:
    assert client.get("/api/trips/missing", headers=AUTH_USER_1).status_code == 404
    assert client.put(
        "/api/trips/missing",
        json={**trip_payload(), "id": "missing"},
        headers=AUTH_USER_1,
    ).status_code == 404
    assert client.delete("/api/trips/missing", headers=AUTH_USER_1).status_code == 404


def test_update_requires_matching_path_and_body_ids(
    supabase_client: FakeSupabase,
) -> None:
    response = client.put(
        "/api/trips/trip-test-1",
        json={**trip_payload(), "id": "another-trip"},
        headers=AUTH_USER_1,
    )
    assert response.status_code == 422


def test_trip_storage_is_unavailable_without_supabase_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trips_route, "get_supabase_client", lambda _access_token: None)
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: None)
    response = client.get("/api/trips", headers=AUTH_USER_1)
    assert response.status_code == 503
    assert "Authentication is unavailable" in response.json()["detail"]


def test_trip_storage_failures_return_a_generic_gateway_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenSupabase:
        auth = FakeSupabase().auth

        def table(self, _name: str) -> Any:
            raise RuntimeError("private provider details")

    monkeypatch.setattr(
        trips_route,
        "get_supabase_client",
        lambda _access_token: BrokenSupabase(),
    )
    monkeypatch.setattr(
        auth_core, "get_supabase_auth_client", lambda: BrokenSupabase()
    )
    response = client.get("/api/trips", headers=AUTH_USER_1)
    assert response.status_code == 502
    assert response.json()["detail"] == "Trip storage could not complete the request."


def test_invalid_storage_api_key_is_logged_safely(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingQuery(FakeQuery):
        def execute(self) -> SimpleNamespace:
            raise APIError(
                {
                    "code": "401",
                    "message": "Invalid API key: DO_NOT_LOG_THIS",
                }
            )

    class FailingStorageClient:
        def table(self, _name: str) -> FailingQuery:
            return FailingQuery([])

    monkeypatch.setattr(
        trips_route,
        "get_supabase_client",
        lambda _access_token: FailingStorageClient(),
    )
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: FakeSupabase())

    response = client.get("/api/trips", headers=AUTH_USER_1)

    assert response.status_code == 502
    assert response.json()["detail"] == "Trip storage could not complete the request."
    assert "Supabase trip list failed (APIError; provider_code=401)" in caplog.text
    assert "DO_NOT_LOG_THIS" not in caplog.text
    assert "Invalid API key" not in caplog.text


def test_trip_endpoints_reject_missing_and_invalid_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeSupabase()
    monkeypatch.setattr(
        trips_route, "get_supabase_client", lambda _access_token: fake_client
    )
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: fake_client)

    missing = client.get("/api/trips")
    invalid = client.get(
        "/api/trips",
        headers={"Authorization": "Bearer expired-or-invalid"},
    )
    assert missing.status_code == 401
    assert invalid.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/trips", None),
        ("GET", "/api/trips/trip-test-1", None),
        ("POST", "/api/trips", trip_payload()),
        ("PUT", "/api/trips/trip-test-1", trip_payload()),
        ("DELETE", "/api/trips/trip-test-1", None),
    ],
)
@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_all_trip_endpoints_reject_missing_and_invalid_tokens(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    authorization: str | None,
) -> None:
    fake_client = FakeSupabase()
    monkeypatch.setattr(
        trips_route, "get_supabase_client", lambda _access_token: fake_client
    )
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: fake_client)

    headers = {"Authorization": authorization} if authorization else {}
    request_args: dict[str, Any] = {"headers": headers}
    if payload is not None:
        request_args["json"] = payload
    response = client.request(method, path, **request_args)
    assert response.status_code == 401


def test_trip_list_accepts_a_valid_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeSupabase()
    received_tokens: list[str] = []
    monkeypatch.setattr(
        trips_route,
        "get_supabase_client",
        lambda access_token: received_tokens.append(access_token) or fake_client,
    )
    monkeypatch.setattr(auth_core, "get_supabase_auth_client", lambda: fake_client)

    response = client.get("/api/trips", headers=AUTH_USER_1)

    assert response.status_code == 200
    assert response.json() == []
    assert received_tokens == ["valid-user-1"]


def test_trip_owner_cannot_read_update_or_delete_another_users_trip(
    supabase_client: FakeSupabase,
) -> None:
    payload = {**trip_payload(), "user_id": "user-2"}
    assert client.post("/api/trips", json=payload, headers=AUTH_USER_1).status_code == 200

    assert client.get("/api/trips", headers=AUTH_USER_2).json() == []
    assert client.get(
        "/api/trips/trip-test-1",
        headers=AUTH_USER_2,
    ).status_code == 404
    updated = {**payload, "title": "Unauthorized edit"}
    assert client.put(
        "/api/trips/trip-test-1",
        json=updated,
        headers=AUTH_USER_2,
    ).status_code == 404
    assert client.delete(
        "/api/trips/trip-test-1",
        headers=AUTH_USER_2,
    ).status_code == 404
    assert supabase_client.rows[0]["user_id"] == "user-1"
    assert supabase_client.rows[0]["trip_data"]["title"] == payload["title"]


def test_legacy_trip_without_owner_is_preserved_and_inaccessible(
    supabase_client: FakeSupabase,
) -> None:
    legacy_row = {
        "id": "legacy-trip",
        "name": "Unclaimed legacy trip",
        "destination": "kyoto",
        "trip_data": trip_payload(),
        "user_id": None,
    }
    supabase_client.rows.append(deepcopy(legacy_row))

    assert client.get("/api/trips", headers=AUTH_USER_1).json() == []
    assert client.get(
        "/api/trips/legacy-trip",
        headers=AUTH_USER_1,
    ).status_code == 404
    assert client.put(
        "/api/trips/legacy-trip",
        json={**trip_payload(), "id": "legacy-trip"},
        headers=AUTH_USER_1,
    ).status_code == 404
    assert client.delete(
        "/api/trips/legacy-trip",
        headers=AUTH_USER_1,
    ).status_code == 404
    assert supabase_client.rows == [legacy_row]
