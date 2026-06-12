import pytest
import responses as rsps

from src.connectors.nyc_cfb import NYCCFBConnector

BASE = "https://www.nyccfb.info"

SAMPLE_CSV = (
    "ELECTION,RECIPID,RECIPNAME,OFFICECD,FILING,SCHEDULE,REFNO,DATE,NAME,"
    "C_CODE,CITY,STATE,ZIP,OCCUPATION,EMPNAME,AMNT,MATCHAMNT,PAY_METHOD\r\n"
    "2021,12345,Jane Smith,5,FULL,ABC,REF001,01/15/2021,John Doe,"
    "IND,Brooklyn,NY,11201,Engineer,ACME Corp,500.00,500.00,2\r\n"
)


@pytest.fixture
def connector():
    return NYCCFBConnector()


@rsps.activate
def test_get_contributions_single_cycle(connector):
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2021_Contributions.csv", body=SAMPLE_CSV)
    records = connector.get_contributions(cycles=[2021])
    assert len(records) == 1
    assert records[0]["RECIPNAME"] == "Jane Smith"
    assert records[0]["cycle_year"] == 2021


@rsps.activate
def test_cycle_year_field_added(connector):
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2021_Contributions.csv", body=SAMPLE_CSV)
    records = connector.get_contributions(cycles=[2021])
    assert "cycle_year" in records[0]
    assert records[0]["cycle_year"] == 2021


@rsps.activate
def test_get_contributions_multiple_cycles(connector):
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2021_Contributions.csv", body=SAMPLE_CSV)
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2023_Contributions.csv", body=SAMPLE_CSV)
    records = connector.get_contributions(cycles=[2021, 2023])
    assert len(records) == 2
    assert records[0]["cycle_year"] == 2021
    assert records[1]["cycle_year"] == 2023


@rsps.activate
def test_unknown_cycle_skipped(connector):
    records = connector.get_contributions(cycles=[1999])
    assert records == []


@rsps.activate
def test_fetch_all_returns_expected_key(connector):
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2021_Contributions.csv", body=SAMPLE_CSV)
    result = connector.fetch_all(cycles=[2021])
    assert set(result.keys()) == {"nyc_cfb_contributions"}
    assert len(result["nyc_cfb_contributions"]) == 1


@rsps.activate
def test_empty_csv_returns_no_records(connector):
    empty_csv = "ELECTION,RECIPID,RECIPNAME,AMNT\r\n"
    rsps.add(rsps.GET, f"{BASE}/DataLibrary/2021_Contributions.csv", body=empty_csv)
    records = connector.get_contributions(cycles=[2021])
    assert records == []
