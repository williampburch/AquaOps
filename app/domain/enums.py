from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    WATER_TEST = "water_test"
    FEEDING = "feeding"
    MAINTENANCE = "maintenance"
    FERTILIZER = "fertilizer"
    NOTE = "note"
    PHOTO = "photo"
    LIVESTOCK_CHANGE = "livestock_change"
    PLANT_CHANGE = "plant_change"
    PROBLEM_CHANGE = "problem_change"


class MeasurementMetric(StrEnum):
    AMMONIA = "ammonia"
    NITRITE = "nitrite"
    NITRATE = "nitrate"
    PH = "ph"
    TEMPERATURE = "temperature"
    KH = "kh"
    GH = "gh"
    TDS = "tds"


class MaintenanceType(StrEnum):
    WATER_CHANGE = "water_change"
    GLASS_CLEANING = "glass_cleaning"
    FILTER_CLEANING = "filter_cleaning"
    SUBSTRATE_VACUUM = "substrate_vacuum"
    EQUIPMENT_REPLACEMENT = "equipment_replacement"
    PLANT_TRIMMING = "plant_trimming"


class FertilizerProductKey(StrEnum):
    SEACHEM_FLOURISH = "seachem_flourish"
    ROOT_TABS = "root_tabs"
    EASY_GREEN = "easy_green"
    CUSTOM = "custom"
