
from typing import List
from pydantic import ValidationError
from .validate import is_valid_hour, is_valid_minute, convert_day_list_to_index, validate_search_ages, validate_countries, validate_continents, validate_sex_options
from ..lib.constants import SortOptions
from ..lib.errors import CronSyntaxParsingException
from .models import SearchOptions


def parse_cron_from_date(minute: int, hour: int, days: List[str]) -> str:
    """
    Generate a cron expression from the given time and days.
    
    :param minute: Minute of the hour (0-59)
    :param hour: Hour of the day (0-23)
    :param days: List of weekday indexes. 0 for sun, 1 for mon and so on
    :return: A valid cron string
    :raises CronSyntaxParsingException: If inputs are invalid
    """
    if not is_valid_minute(minute):
        raise CronSyntaxParsingException(f"Invalid minute: {minute}. Must be between 0 and 59.")
    
    if not is_valid_hour(hour):
        raise CronSyntaxParsingException(f"Invalid hour: {hour}. Must be between 0 and 23.")
    
    days_index_list = convert_day_list_to_index(days)
    if not days_index_list:
        raise CronSyntaxParsingException(f"Invalid or empty days list: {days}. Must contain valid day names.")
    
    days_syntax = ",".join(map(str, days_index_list))
    cron_syntax = f"{minute} {hour} * * {days_syntax}"
    return cron_syntax


def parse_and_validate_search_options(options: dict):
    params = {
            'sort': options.get('sort', SortOptions.LAST_LOGIN),
            'age1': options.get('age1', '16'),
            'age2': options.get('age2', '110'),
            'sex': options.get('sex', ['male', 'female']),
            'continents': options.get('continents', ['AF', 'AS', 'EU', 'NA', 'OC', 'SA']),
            'countries': options.get('countries', ['---']),
            'keywords': options.get('keywords', ''),
        }
      
    if options.get('online'):
            params['online'] = '1'

    if options.get('photo'):
            params['photo'] = '1'
    try:
        s_options = SearchOptions(**params)
        s_options.sex = validate_sex_options(s_options.sex)
        ages = validate_search_ages(s_options.age1, s_options.age2)
        s_options.age1, s_options.age2 = ages[0], ages[1]
        s_options.continents = validate_continents(s_options.continents)
        if s_options.countries == ['---']:
            return s_options
        s_options.countries = validate_countries(s_options.countries)
        return s_options
    
    except ValidationError as e:
        raise ValueError(f"Search options validation failed: {str(e)}")
    
