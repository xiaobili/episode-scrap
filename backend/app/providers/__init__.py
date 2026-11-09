from app.providers.base import BaseProvider, ProviderNotConfigured
from app.providers.tmdb import TMDBProvider


def get_provider(name: str, api_key: str) -> BaseProvider:
    if name == "tmdb":
        return TMDBProvider(api_key=api_key)
    raise ProviderNotConfigured(f"未知媒体源：{name}")
