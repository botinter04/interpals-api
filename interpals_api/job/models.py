from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from ..lib.constants import ContinentCode, Genders, CountryCode, SortOptions


class JobType(Enum):
    SEARCH = "search"
    CHAT = "chat"

class JobConfigRequest(BaseModel): 
    job_name: str
    min: int
    hour: int
    days: List[str]
    type: JobType
    data: Optional[object] = None


class SearchOptions(BaseModel):
    age1: Optional[str] = "16"
    age2: Optional[str] = "110"
    sex: Optional[List[Genders]] = ["male", "female"]
    continents: Optional[List[ContinentCode]] = ["AF", "AS", "EU", "NA", "OC", "SA"]
    countries: Optional[List[CountryCode]] = ["---"]
    keywords: Optional[str] = ""
    online: Optional[bool] = False
    photo: Optional[bool] = False
    city: Optional[str] = None
    cityName: Optional[str] = None
    sort: SortOptions = SortOptions.NEWEST_FIRST
    limit: Optional[int] = 1000
    timeout: Optional[float] = 0.0