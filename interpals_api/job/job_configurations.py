from enum import Enum
from typing import List, Optional
from fastapi import HTTPException
from pydantic import BaseModel
from interpals_api.job.parsers import parse_and_validate_search_options, parse_cron_from_date
from interpals_api.job.validators import validate_days
from interpals_api.lib.constants import ContinentCode, CountryCode, Genders, SortOptions
from interpals_api.store.store import redis_client
from interpals_api.lib.errors import ExistingKeyException
import json

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


REDIS_JOB_BASE_KEY = "config:job"

async def add_cron_job(job: JobConfigRequest):
    job_name = f"{REDIS_JOB_BASE_KEY}:{job.job_name}"
    try:
        existing_job = redis_client.get(job_name)
        if existing_job is not None:
            raise ExistingKeyException("A job with this name already exists.")
        #todo: add other cron job validations - jobs must be spaced at least an hour apart, not more than a specified number daily
        days = validate_days(job.days)
        if job.type == JobType.SEARCH:
            job.data = parse_and_validate_search_options(job.data)

        job_dict = {
            "cron_time": parse_cron_from_date(job.min, job.hour, days),
            "job_type": str(job.type),
            "data": job.data,
        }
        redis_client.set(job_name, json.dumps(job_dict))
        return job_name

    except ExistingKeyException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error adding job: {str(e)}")


async def get_cron_jobs():
    try:
        jobs = redis_client.get_values_with_prefix(REDIS_JOB_BASE_KEY)
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve jobs: {str(e)}")


async def count_cron_jobs():
    try:
        return redis_client.count_keys_with_prefix(REDIS_JOB_BASE_KEY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to count jobs: {str(e)}")