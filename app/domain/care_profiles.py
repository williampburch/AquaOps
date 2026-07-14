from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CareProfile:
    key: str
    label: str
    summary: str
    schedule_intervals: dict[str, int]


CARE_PROFILES = {
    profile.key: profile
    for profile in (
        CareProfile(
            "simple_care",
            "Simple Care",
            "Essential feeding, weekly water changes, and filter care.",
            {"feeding": 1, "water_change": 7, "filter_cleaning": 30},
        ),
        CareProfile(
            "water_testing",
            "Water Testing",
            "Simple care plus a weekly parameter check.",
            {
                "feeding": 1,
                "water_change": 7,
                "filter_cleaning": 30,
                "water_test": 7,
            },
        ),
        CareProfile(
            "planted_tank",
            "Planted Tank",
            "Balanced low-tech plant care with fertilizer and trimming reminders.",
            {
                "feeding": 1,
                "water_change": 7,
                "filter_cleaning": 30,
                "fertilizer": 7,
                "plant_trimming": 30,
            },
        ),
        CareProfile(
            "high_tech_planted",
            "High-Tech Planted",
            "More frequent fertilizer, testing, trimming, and filter care.",
            {
                "feeding": 1,
                "water_change": 7,
                "filter_cleaning": 21,
                "fertilizer": 3,
                "plant_trimming": 14,
                "water_test": 7,
            },
        ),
        CareProfile(
            "breeder_grow_out",
            "Breeder / Grow-Out",
            "Frequent water changes with daily feeding and closer testing.",
            {
                "feeding": 1,
                "water_change": 3,
                "filter_cleaning": 14,
                "water_test": 7,
            },
        ),
        CareProfile(
            "quarantine",
            "Quarantine",
            "Short-interval testing and water changes for active observation.",
            {
                "feeding": 1,
                "water_change": 3,
                "filter_cleaning": 7,
                "water_test": 2,
            },
        ),
        CareProfile(
            "custom",
            "Custom",
            "Start with schedules off and configure each one yourself.",
            {},
        ),
    )
}


def care_profile(profile_key: str) -> CareProfile:
    return CARE_PROFILES.get(profile_key, CARE_PROFILES["custom"])
