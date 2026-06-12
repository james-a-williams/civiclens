from unittest.mock import MagicMock, patch

from src.connectors.snowflake_loader import load_all, load_connector_data, load_table

RECORDS = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@patch("src.connectors.snowflake_loader.write_pandas")
def test_load_table_adds_load_at(mock_write):
    conn = MagicMock()
    load_table(conn, RECORDS, "test_table")
    df = mock_write.call_args[0][1]
    assert "LOAD_AT" in df.columns


@patch("src.connectors.snowflake_loader.write_pandas")
def test_load_table_skips_empty_records(mock_write):
    conn = MagicMock()
    load_table(conn, [], "test_table")
    mock_write.assert_not_called()


@patch("src.connectors.snowflake_loader.write_pandas")
def test_load_table_correct_table_name(mock_write):
    conn = MagicMock()
    load_table(conn, RECORDS, "my_table")
    assert mock_write.call_args[0][2] == "MY_TABLE"


@patch("src.connectors.snowflake_loader.load_table")
def test_load_connector_data_calls_load_table_for_each_key(mock_load_table):
    conn = MagicMock()
    tables = {"table_a": RECORDS, "table_b": RECORDS}
    load_connector_data(conn, tables)
    assert mock_load_table.call_count == 2
    mock_load_table.assert_any_call(conn, RECORDS, "table_a")
    mock_load_table.assert_any_call(conn, RECORDS, "table_b")


def _fake_connector_cls(name):
    cls = MagicMock()
    cls.SOURCE_NAME = name
    cls.return_value.fetch_all.return_value = {}
    return cls


@patch("src.connectors.snowflake_loader.get_raw_connection")
def test_load_all_calls_each_connector(mock_get_conn, monkeypatch):
    # load_all iterates the module-level CONNECTORS list, so patching the
    # class attributes individually would leave the originals in the list.
    monkeypatch.setattr("sys.argv", ["civiclens-load"])
    fakes = [
        _fake_connector_cls(name)
        for name in ("congress", "fec", "openstates", "census", "ny_boe", "nyc_cfb")
    ]
    monkeypatch.setattr(
        "src.connectors.snowflake_loader.CONNECTORS", [(cls, "") for cls in fakes]
    )

    load_all()

    for cls in fakes:
        cls.return_value.fetch_all.assert_called_once()
    mock_get_conn.return_value.close.assert_called_once()
