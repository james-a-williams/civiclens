import pytest

from src.connectors.base import ConnectorError
from src.connectors.ny_boe import NYBOEConnector

SAMPLE_HEADER = "Election Year,Filer ID,Committee Name,Candidate Name,Office,District,Public Funds Received,Qualified Campaign Expenditures\n"
SAMPLE_ROW = '2024,13466,Friends of Jane Smith,Jane Smith,Member of Assembly,42,50000.00,45000.00\n'


@pytest.fixture
def connector():
    return NYBOEConnector()


def test_get_activity_reads_single_csv(connector, tmp_path):
    (tmp_path / "activity_2024.csv").write_text(SAMPLE_HEADER + SAMPLE_ROW)
    records = connector.get_activity(data_dir=tmp_path)
    assert len(records) == 1
    assert records[0]["Candidate Name"] == "Jane Smith"
    assert records[0]["Election Year"] == "2024"
    assert records[0]["District"] == "42"


def test_get_activity_combines_multiple_files(connector, tmp_path):
    (tmp_path / "activity_2024.csv").write_text(SAMPLE_HEADER + SAMPLE_ROW)
    (tmp_path / "activity_2025.csv").write_text(
        SAMPLE_HEADER + '2025,99999,Committee B,Bob Jones,State Senator,12,75000.00,70000.00\n'
    )
    records = connector.get_activity(data_dir=tmp_path)
    assert len(records) == 2
    years = {r["Election Year"] for r in records}
    assert years == {"2024", "2025"}


def test_get_activity_empty_public_funds_allowed(connector, tmp_path):
    row_no_funds = '2024,13466,Friends of Jane Smith,Jane Smith,Member of Assembly,42,,\n'
    (tmp_path / "activity_2024.csv").write_text(SAMPLE_HEADER + row_no_funds)
    records = connector.get_activity(data_dir=tmp_path)
    assert len(records) == 1
    assert records[0]["Public Funds Received"] == ""


def test_missing_directory_raises(connector, tmp_path):
    with pytest.raises(ConnectorError, match="not found"):
        connector.get_activity(data_dir=tmp_path / "nonexistent")


def test_empty_directory_raises(connector, tmp_path):
    with pytest.raises(ConnectorError, match="No CSV files"):
        connector.get_activity(data_dir=tmp_path)


def test_fetch_all_returns_expected_key(connector, tmp_path):
    (tmp_path / "activity_2024.csv").write_text(SAMPLE_HEADER + SAMPLE_ROW)
    result = connector.fetch_all(data_dir=tmp_path)
    assert set(result.keys()) == {"ny_boe_activity"}
    assert len(result["ny_boe_activity"]) == 1
