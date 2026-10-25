
"""Загрузка синтетических профилей для демонстрационного режима."""

import json
from functools import lru_cache
from pathlib import Path

from app.contracts import ClientProfile


PROFILES_PATH = Path(__file__).with_name("profiles.json")


@lru_cache(maxsize=1)
def load_demo_profiles() -> dict[str, ClientProfile]:
    """Загружает и валидирует демо-профили из JSON."""
    with PROFILES_PATH.open("r", encoding="utf-8") as file:
        raw_profiles = json.load(file)

    if not isinstance(raw_profiles, list):
        raise ValueError("profiles.json должен содержать JSON-массив")

    profiles: dict[str, ClientProfile] = {}

    for raw_profile in raw_profiles:
        profile = ClientProfile.model_validate(raw_profile)

        if profile.client_id in profiles:
            raise ValueError(
                f"Повторяющийся client_id: {profile.client_id}"
            )

        profiles[profile.client_id] = profile

    return profiles


def get_demo_profile(client_id: str) -> ClientProfile | None:
    """Возвращает демо-профиль по ID."""
    return load_demo_profiles().get(client_id)

