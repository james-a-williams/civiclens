import pytest
import requests
import responses as rsps

from src.connectors.base import BaseConnector, ConnectorError


class _Connector(BaseConnector):
    SOURCE_NAME = "test"
    BASE_URL = "https://api.example.com"

    def fetch_all(self):
        return {}


@pytest.fixture
def connector():
    return _Connector()


@rsps.activate
def test_get_returns_json(connector):
    rsps.add(rsps.GET, "https://api.example.com/items", json={"items": [1, 2, 3]})
    result = connector._get("/items")
    assert result == {"items": [1, 2, 3]}


@rsps.activate
def test_get_raises_on_4xx(connector):
    rsps.add(rsps.GET, "https://api.example.com/items", status=401)
    with pytest.raises(requests.HTTPError):
        connector._get("/items")


@rsps.activate
def test_paginate_single_page(connector):
    rsps.add(
        rsps.GET,
        "https://api.example.com/items",
        json={"results": [{"id": 1}], "pagination": {"page": 1, "pages": 1}},
    )
    records = list(connector._paginate("/items", {}, "results"))
    assert records == [{"id": 1}]


@rsps.activate
def test_paginate_multiple_pages(connector):
    rsps.add(
        rsps.GET,
        "https://api.example.com/items",
        json={"results": [{"id": 1}], "pagination": {"page": 1, "pages": 2}},
    )
    rsps.add(
        rsps.GET,
        "https://api.example.com/items",
        json={"results": [{"id": 2}], "pagination": {"page": 2, "pages": 2}},
    )
    records = list(connector._paginate("/items", {}, "results"))
    assert [r["id"] for r in records] == [1, 2]


@rsps.activate
def test_paginate_empty_results(connector):
    rsps.add(rsps.GET, "https://api.example.com/items", json={"results": [], "pagination": {}})
    records = list(connector._paginate("/items", {}, "results"))
    assert records == []


def test_to_parquet_writes_file(connector, tmp_path, monkeypatch):
    import src.connectors.base as base_module
    monkeypatch.setattr(base_module, "RAW_DIR", tmp_path)
    path = connector.to_parquet([{"id": 1, "name": "test"}], "items")
    assert path is not None
    assert path.exists()


def test_to_parquet_empty_returns_none(connector):
    result = connector.to_parquet([], "items")
    assert result is None
