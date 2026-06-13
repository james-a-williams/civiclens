import pandas as pd
import streamlit as st
from api_client import get

st.title("🔍 Find Candidates")
st.caption("Search federal (FEC), NY state (BOE), and NYC local (CFB) candidates.")

with st.sidebar:
    st.header("Filters")
    level = st.selectbox("Level", ["All", "federal", "state", "local"])
    state = st.text_input("State (2-letter)", max_chars=2)
    cycle = st.selectbox("Cycle", ["All", 2026, 2025, 2024, 2023, 2021, 2019, 2017])
    office = st.text_input("Office contains")
    party = st.text_input("Party contains")

q = st.text_input("Candidate name", placeholder="e.g. Ocasio-Cortez, Mamdani, Hochul")

page_size = 25
if "search_offset" not in st.session_state:
    st.session_state.search_offset = 0

filters = {
    "q": q or None,
    "level": None if level == "All" else level,
    "state": state or None,
    "cycle": None if cycle == "All" else cycle,
    "office": office or None,
    "party": party or None,
}

data = get("/candidates", limit=page_size, offset=st.session_state.search_offset, **filters)
results, total = data["results"], data["total"]

st.write(f"**{total:,}** candidacies found")

if results:
    df = pd.DataFrame(results)
    display_cols = ["display_name", "party", "level", "office", "state", "district", "cycle"]
    event = st.dataframe(
        df[display_cols],
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "display_name": "Name",
            "party": "Party",
            "level": "Level",
            "office": "Office",
            "state": "State",
            "district": "District",
            "cycle": "Cycle",
        },
    )
    if event.selection.rows:
        st.session_state.candidacy_key = df.iloc[event.selection.rows[0]]["candidacy_key"]
        st.switch_page("views/profile.py")

    col_prev, col_page, col_next = st.columns([1, 2, 1])
    if col_prev.button("← Previous", disabled=st.session_state.search_offset == 0):
        st.session_state.search_offset -= page_size
        st.rerun()
    col_page.caption(
        f"Showing {st.session_state.search_offset + 1}–"
        f"{min(st.session_state.search_offset + page_size, total)} of {total:,}"
    )
    if col_next.button("Next →", disabled=st.session_state.search_offset + page_size >= total):
        st.session_state.search_offset += page_size
        st.rerun()
else:
    st.info("No candidates match. Try loosening the filters.")
