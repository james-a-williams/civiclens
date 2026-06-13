import streamlit as st

st.set_page_config(page_title="CivicLens", page_icon="🏛️", layout="wide")

pg = st.navigation(
    [
        st.Page("views/find_candidates.py", title="Find Candidates", icon="🔍", default=True),
        st.Page("views/profile.py", title="Candidate Profile", icon="👤"),
    ]
)
pg.run()
