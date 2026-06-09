import logging
import os
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import BaseConnector

logger = logging.getLogger(__name__)

ACS_YEAR = 2023

# Core demographic variables for district context
DISTRICT_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B02001_002E": "pop_white_alone",
    "B02001_003E": "pop_black_alone",
    "B03001_003E": "pop_hispanic_latino",
    "B15003_022E": "pop_bachelors_degree",
    "B27001_001E": "pop_health_insurance",
}


class CensusConnector(BaseConnector):
    """Census Bureau API — ACS 5-year demographic estimates by congressional district.

    Returns data as list of dicts with variable names mapped to readable field names.
    No pagination — all geographies returned in a single response.
    Docs: https://www.census.gov/data/developers/about.html
    """

    SOURCE_NAME = "census"
    BASE_URL = "https://api.census.gov/data"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key or os.environ["CENSUS_API_KEY"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _census_get(self, path: str, params: dict[str, Any]) -> list[list[str]]:
        """Census API returns a 2D list: first row is headers, rest are values."""
        url = f"{self.BASE_URL}{path}"
        params = {**params, "key": self._api_key}
        logger.debug("GET %s params=%s", url, {k: v for k, v in params.items() if k != "key"})
        resp = self._session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _to_records(self, raw: list[list[str]], variable_map: dict[str, str]) -> list[dict]:
        """Convert Census 2D response into list of dicts with readable field names."""
        headers = raw[0]
        records = []
        for row in raw[1:]:
            record = dict(zip(headers, row))
            renamed = {}
            for key, value in record.items():
                renamed[variable_map.get(key, key)] = value
            records.append(renamed)
        return records

    def get_congressional_districts(
        self,
        variables: dict[str, str] | None = None,
        year: int = ACS_YEAR,
    ) -> list[dict]:
        """Fetch ACS 5-year estimates for all congressional districts in all states."""
        var_map = variables or DISTRICT_VARIABLES
        get_vars = ",".join(["NAME"] + list(var_map.keys()))
        raw = self._census_get(
            f"/{year}/acs/acs5",
            {
                "get": get_vars,
                "for": "congressional district:*",
                "in": "state:*",
            },
        )
        return self._to_records(raw, var_map)

    def get_state_demographics(
        self,
        variables: dict[str, str] | None = None,
        year: int = ACS_YEAR,
    ) -> list[dict]:
        """Fetch ACS 5-year estimates at the state level."""
        var_map = variables or DISTRICT_VARIABLES
        get_vars = ",".join(["NAME"] + list(var_map.keys()))
        raw = self._census_get(
            f"/{year}/acs/acs5",
            {"get": get_vars, "for": "state:*"},
        )
        return self._to_records(raw, var_map)

    def fetch_all(self, year: int = ACS_YEAR) -> dict[str, list[dict]]:  # type: ignore[override]
        logger.info("Census: fetching congressional district demographics year=%d", year)
        districts = self.get_congressional_districts(year=year)

        logger.info("Census: fetching state demographics year=%d", year)
        states = self.get_state_demographics(year=year)

        return {"congressional_districts": districts, "states": states}
