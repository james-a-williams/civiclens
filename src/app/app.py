import streamlit as st

st.set_page_config(page_title="CivicLens", page_icon="🏛️", layout="wide")

pg = st.navigation(
    [
        st.Page("views/find_members.py", title="Find Officials", icon="🔍", default=True),
        st.Page("views/member_profile.py", title="Official Profile", icon="👤"),
    ]
)
pg.run()
