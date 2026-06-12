import os

import requests
import streamlit as st

API_BASE = os.environ.get("CIVICLENS_API_URL", "http://localhost:8000")


@st.cache_data(ttl=300, show_spinner=False)
def get(path: str, **params) -> dict:
    resp = requests.get(
        f"{API_BASE}{path}",
        params={k: v for k, v in params.items() if v is not None},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def to_float(value) -> float | None:
    """API serializes Snowflake decimals as strings; charts need floats."""
    return None if value is None else float(value)
