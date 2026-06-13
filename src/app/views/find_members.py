import pandas as pd
import streamlit as st
from api_client import get

st.title("Find Federal Officials")
st.caption("Search U.S. House members and Senators serving since 2009 (111th Congress onward).")

with st.sidebar:
    st.header("Filters")
    chamber = st.selectbox("Chamber", ["All", "house", "senate"])
    state = st.text_input("State (2-letter)", max_chars=2)
    party = st.text_input("Party contains")
    congress = st.selectbox(
        "Congress",
        ["All"] + list(range(119, 110, -1)),
        format_func=lambda x: "All" if x == "All" else f"{x}th Congress",
    )

q = st.text_input("Name", placeholder="e.g. Warren, AOC, McConnell")

page_size = 25
if "member_offset" not in st.session_state:
    st.session_state.member_offset = 0

filters = {
    "q": q or None,
    "chamber": None if chamber == "All" else chamber,
    "state": state or None,
    "party": party or None,
    "congress": None if congress == "All" else congress,
}

data = get(
    "/members",
    limit=page_size,
    offset=st.session_state.member_offset,
    **filters,
)
results, total = data["results"], data["total"]

st.write(f"**{total:,}** officials found")

if results:
    df = pd.DataFrame(results)
    display_cols = ["display_name", "party", "chamber", "state", "district", "latest_congress"]
    event = st.dataframe(
        df[display_cols],
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "display_name": "Name",
            "party": "Party",
            "chamber": "Chamber",
            "state": "State",
            "district": "District",
            "latest_congress": "Latest Congress",
        },
    )
    if event.selection.rows:
        st.session_state.member_key = df.iloc[event.selection.rows[0]]["member_key"]
        st.switch_page("views/member_profile.py")

    col_prev, col_page, col_next = st.columns([1, 2, 1])
    if col_prev.button("← Previous", disabled=st.session_state.member_offset == 0):
        st.session_state.member_offset -= page_size
        st.rerun()
    col_page.caption(
        f"Showing {st.session_state.member_offset + 1}–"
        f"{min(st.session_state.member_offset + page_size, total)} of {total:,}"
    )
    if col_next.button(
        "Next →",
        disabled=st.session_state.member_offset + page_size >= total,
    ):
        st.session_state.member_offset += page_size
        st.rerun()
else:
    st.info("No officials match. Try loosening the filters.")
