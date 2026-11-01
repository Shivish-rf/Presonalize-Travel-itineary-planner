from functools import lru_cache

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import settings


@lru_cache(maxsize=1)
def _create_auth_client(url: str, api_key: str) -> Client:
    return create_client(url, api_key)


def get_supabase_client(access_token: str) -> Client | None:
    if (
        not settings.supabase_url
        or not settings.supabase_auth_api_key
        or not access_token
    ):
        return None
    options = SyncClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
        auto_refresh_token=False,
        persist_session=False,
    )
    return create_client(
        settings.supabase_url,
        settings.supabase_auth_api_key,
        options,
    )


def get_supabase_auth_client() -> Client | None:
    if not settings.supabase_url or not settings.supabase_auth_api_key:
        return None
    return _create_auth_client(settings.supabase_url, settings.supabase_auth_api_key)
