import os
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)


def _load_private_key() -> bytes:
    key_path = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser()
    pem = key_path.read_bytes()
    private_key = load_pem_private_key(pem, password=None, backend=default_backend())
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


def get_connection(
    database: str | None = None, schema: str | None = None
) -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_load_private_key(),
        role=os.environ.get("SNOWFLAKE_ROLE", "CIVICLENS"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CIVICLENS_WH"),
        database=database or os.environ.get("SNOWFLAKE_DATABASE", "CIVICLENS"),
        schema=schema,
    )


def get_raw_connection() -> snowflake.connector.SnowflakeConnection:
    return get_connection(
        database=os.environ.get("SNOWFLAKE_RAW_DATABASE", "CIVICLENS_RAW"),
        schema=os.environ.get("SNOWFLAKE_RAW_SCHEMA", "PUBLIC"),
    )
