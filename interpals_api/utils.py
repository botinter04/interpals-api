import re
from typing import Optional, Union, List, Type
from enum import Enum

re_csfr_token = re.compile(r'<meta name="csrf_token" content="(.*?)"')


def find_csrf_token(html):
    match = re_csfr_token.search(html)
    if match is not None:
        return match.group(1)
    else:
        return None

def validate_enum_list(
    values: Optional[List[str]],
    valid_enum: Union[Type[Enum], List[str]],
    value_name: str = "value"
) -> List[str]:
    if isinstance(valid_enum, type) and issubclass(valid_enum, Enum):
        valid_values = [e.value for e in valid_enum]
    else:
        valid_values = list(valid_enum)

    if values is None:
        return valid_values

    for val in values:
        if val not in valid_values:
            raise ValueError(f"Invalid {value_name}: {val}. Must be one of {valid_values}")
    
    return values