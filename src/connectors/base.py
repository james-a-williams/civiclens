import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")


class ConnectorError(Exception):
    pass


class BaseConnector(ABC):
    SOURCE_NAME: str = ""
    BASE_URL: str = ""

    def __init__(self) -> None:
        self._session = requests.Session()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        logger.debug("GET %s params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 30))
            logger.warning("429 rate limit — sleeping %ds before retry", retry_after)
            time.sleep(retry_after)
        resp.raise_for_status()
        return resp.json()

    def _paginate(
        self,
        path: str,
        params: dict[str, Any],
        results_key: str,
        page_key: str = "page",
        per_page_key: str = "per_page",
        per_page: int = 100,
    ) -> Iterator[dict]:
        """Yield records from page-based paginated endpoints."""
        params = {**params, page_key: 1, per_page_key: per_page}
        while True:
            data = self._get(path, params)
            records = data.get(results_key, [])
            if not records:
                break
            yield from records
            pagination = data.get("pagination", {})
            if params[page_key] >= pagination.get("pages", 1):
                break
            params[page_key] += 1

    def to_parquet(self, records: list[dict], table_name: str) -> Path | None:
        if not records:
            logger.warning("%s: no records for %s", self.SOURCE_NAME, table_name)
            return None
        out_dir = RAW_DIR / self.SOURCE_NAME
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{table_name}.parquet"
        pq.write_table(pa.Table.from_pylist(records), path)
        logger.info("%s: wrote %d records → %s", self.SOURCE_NAME, len(records), path)
        return path

    @abstractmethod
    def fetch_all(self) -> dict[str, list[dict]]:
        """Fetch all tables for this source. Returns {table_name: [records]}."""
        ...
