from typing import List, Optional
from ..lib.constants import Genders, ContinentCode, CountryCode
from ..utils import validate_enum_list

def validate_search_ages(age1: Optional[int], age2: Optional[int]):
    age1 = age1 if age1 is not None else 16
    age2 = age2 if age2 is not None else 120

    if age2 < age1:
        raise ValueError(f"age2 ({age2}) cannot be less than age1 ({age1})")

    return [age1, age2]

def is_valid_minute(min_val: int) -> bool:
    return 0 <= min_val <= 59

def is_valid_hour(hour: int) -> bool:
    return 0 <= hour <= 23

def validate_days(days: List[str]) -> List[int]:
    if not days:
        return []

    days_map = {
        'sun': 0,
        'mon': 1,
        'tue': 2,
        'wed': 3,
        'thu': 4,
        'fri': 5,
        'sat': 6
    }

    valid_days = []
    for day in days:
        day_lower = day.lower()
        if day_lower in days_map:
            valid_days.append(days_map[day_lower])

    return valid_days

def validate_sex_options(sexes: Optional[List[str]]):
    return validate_enum_list(sexes, Genders, 'gender')

def validate_continents(continents: Optional[List[str]]):
    return validate_enum_list(continents, ContinentCode, 'continent')

def validate_countries(countries: Optional[List[str]]):
    return validate_enum_list(countries, CountryCode, 'country')

