"""Embedded knowledge base for real LLM experiment.

18 factual entries used as ground truth for multi-hop questions.
"""

from __future__ import annotations

from typing import Dict


KB: Dict[str, Dict[str, str]] = {
    "eiffel_tower": {
        "name": "Eiffel Tower",
        "height": "330 meters",
        "height_m": "330",
        "location": "Paris, France",
        "built": "1889",
        "architect": "Gustave Eiffel",
        "visitors_per_year": "7000000",
    },
    "tokyo": {
        "name": "Tokyo",
        "population": "13960000",
        "country": "Japan",
        "area_km2": "2194",
        "founded": "1457",
        "timezone": "UTC+9",
    },
    "speed_of_light": {
        "name": "Speed of Light",
        "value": "299792458",
        "unit": "meters per second",
        "symbol": "c",
        "discovery_credit": "Ole Roemer (1676)",
    },
    "mars": {
        "name": "Mars",
        "distance_from_sun_km": "227900000",
        "orbital_period_days": "687",
        "diameter_km": "6779",
        "gravity_m_s2": "3.721",
        "moons": "2",
    },
    "python_language": {
        "name": "Python",
        "creator": "Guido van Rossum",
        "first_release": "1991",
        "latest_version": "3.12",
        "type": "interpreted",
        "paradigm": "multi-paradigm",
    },
    "amazon_river": {
        "name": "Amazon River",
        "length_km": "6400",
        "discharge_m3_s": "209000",
        "countries": "Brazil, Peru, Colombia",
        "basin_area_km2": "7050000",
    },
    "human_body": {
        "name": "Human Body",
        "bones": "206",
        "muscles": "600",
        "blood_volume_liters": "5",
        "normal_temperature_c": "37",
        "heart_rate_bpm": "72",
    },
    "moon": {
        "name": "Moon",
        "distance_km": "384400",
        "diameter_km": "3474",
        "orbital_period_days": "27.3",
        "gravity_m_s2": "1.62",
        "first_landing": "1969",
    },
    "bitcoin": {
        "name": "Bitcoin",
        "creator": "Satoshi Nakamoto",
        "created_year": "2009",
        "max_supply": "21000000",
        "block_time_minutes": "10",
        "algorithm": "SHA-256",
    },
    "mount_everest": {
        "name": "Mount Everest",
        "height_m": "8849",
        "location": "Nepal/Tibet",
        "first_summit": "1953",
        "first_summiteers": "Edmund Hillary and Tenzing Norgay",
    },
    "earth": {
        "name": "Earth",
        "diameter_km": "12742",
        "mass_kg": "5.972e24",
        "age_years": "4540000000",
        "distance_from_sun_km": "149600000",
        "orbital_period_days": "365.25",
        "rotation_period_hours": "24",
    },
    "water": {
        "name": "Water",
        "chemical_formula": "H2O",
        "boiling_point_c": "100",
        "freezing_point_c": "0",
        "density_kg_m3": "1000",
        "molar_mass_g_mol": "18.015",
    },
    "sun": {
        "name": "Sun",
        "diameter_km": "1392700",
        "mass_solar": "1",
        "surface_temp_c": "5500",
        "age_years": "4600000000",
        "type": "G-type main-sequence star",
    },
    "great_wall": {
        "name": "Great Wall of China",
        "length_km": "21196",
        "construction_start": "7th century BC",
        "construction_end": "17th century AD",
        "location": "China",
    },
    "dna": {
        "name": "DNA",
        "full_name": "Deoxyribonucleic acid",
        "bases": "adenine, thymine, guanine, cytosine",
        "base_pairs_human": "3200000000",
        "discoverers": "Watson and Crick (1953)",
        "double_helix_width_nm": "2",
    },
    "olympic_games": {
        "name": "Olympic Games",
        "origin": "Olympia, Greece",
        "first_modern": "1896",
        "first_modern_city": "Athens",
        "summer_frequency_years": "4",
        "winter_frequency_years": "4",
    },
    "internet": {
        "name": "Internet",
        "predecessor": "ARPANET",
        "arpanet_year": "1969",
        "www_invention_year": "1989",
        "www_inventor": "Tim Berners-Lee",
        "users_billions": "5.3",
    },
    "sound": {
        "name": "Sound",
        "speed_air_m_s": "343",
        "speed_water_m_s": "1480",
        "speed_steel_m_s": "5960",
        "frequency_unit": "Hertz",
        "human_hearing_range_hz": "20-20000",
    },
}
