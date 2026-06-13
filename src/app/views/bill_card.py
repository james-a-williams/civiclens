"""Shared bill card component — used in the Record tab and Bill Explorer."""

import streamlit as st


def render(bill: dict) -> None:
    level_badge = {"state": "🟨 State", "federal": "🟦 Federal"}.get(
        bill.get("level", ""), ""
    )
    location_parts = [
        level_badge,
        bill.get("state"),
        bill.get("session") or (f"Congress {bill['congress']}" if bill.get("congress") else None),
    ]
    location = " · ".join(str(p) for p in location_parts if p)

    hdr, badge_col = st.columns([6, 1])
    with hdr:
        st.markdown(f"**{bill['identifier']}** — {bill['title']}")
        if location:
            st.caption(location)
    with badge_col:
        if bill.get("is_primary"):
            st.caption("⭐ Primary")

    if bill.get("abstract"):
        st.markdown(bill["abstract"])
    elif bill.get("eli5"):
        st.markdown(f"_{bill['eli5']}_")

    if st.button("View details", key=f"bill_nav_{bill['bill_key']}"):
        st.session_state["bill_key"] = bill["bill_key"]
        st.switch_page("views/bills.py")
