import pandas as pd
import streamlit as st
from api_client import get, to_float

key = st.session_state.get("member_key")
if not key:
    st.info("Pick an official from **Find Officials** to see their profile.")
    st.stop()

profile = get(f"/members/{key}")

chamber_badge = {"senate": "🟦 Senator", "house": "🟩 Representative"}.get(
    profile["chamber"], ""
)
st.title(profile["name"])
subtitle_parts = [
    chamber_badge,
    profile["party"],
    profile["state"],
    f"District {profile['district']}" if profile.get("district") else None,
    f"{profile['latest_congress']}th Congress",
]
st.caption(" · ".join(str(p) for p in subtitle_parts if p))

overview_tab, finance_tab, record_tab, conflict_tab = st.tabs(
    ["Overview", "Finance", "Record", "Conflict of Interest"]
)

# ── Overview ───────────────────────────────────────────────────────────────────

with overview_tab:
    committees = profile.get("committees", [])
    if committees:
        st.subheader("Committee assignments")
        current = [c for c in committees if c["congress"] == profile["latest_congress"]]
        df = pd.DataFrame(current or committees[:10])
        cols = [c for c in ["committee_name", "role_title", "industry_category", "congress"]
                if c in df.columns]
        st.dataframe(
            df[cols],
            hide_index=True,
            column_config={
                "committee_name": "Committee",
                "role_title": "Role",
                "industry_category": "Regulated industry",
                "congress": "Congress",
            },
        )
    else:
        st.caption("No committee assignment data available yet.")

# ── Finance ────────────────────────────────────────────────────────────────────

with finance_tab:
    finance = get(f"/members/{key}/finance")
    cycles = finance.get("cycles", [])

    if not cycles:
        st.caption("No FEC campaign finance data found for this official.")
    else:
        latest = cycles[0]
        st.subheader(f"{latest['cycle']} cycle")
        st.caption("Source: Federal Election Commission")

        m1, m2, m3 = st.columns(3)
        m1.metric("Total raised", f"${to_float(latest['total_receipts']):,.0f}"
                  if latest["total_receipts"] else "—")
        m2.metric("Total spent", f"${to_float(latest['total_disbursements']):,.0f}"
                  if latest["total_disbursements"] else "—")
        m3.metric("Cash on hand", f"${to_float(latest['cash_on_hand']):,.0f}"
                  if latest["cash_on_hand"] else "—")

        st.markdown("#### Fundraising breakdown")
        breakdown = {
            "Individual (itemized)": to_float(
                latest["individual_itemized_contributions"]
            ),
            "Individual (small-dollar)": to_float(
                latest["individual_unitemized_contributions"]
            ),
            "PACs & committees": to_float(latest["pac_contributions"]),
            "Party committees": to_float(latest["party_contributions"]),
            "Self-funding": to_float(latest["candidate_self_funding"]),
        }
        chart_data = {k: v for k, v in breakdown.items() if v}
        if chart_data:
            st.bar_chart(
                pd.DataFrame.from_dict(
                    {"amount": chart_data}, orient="columns"
                ),
                horizontal=True,
            )
            pac_pct = to_float(latest.get("pac_pct_of_total"))
            if pac_pct is not None:
                st.caption(
                    f"PAC/committee money: **{pac_pct:.1f}%** of total raised"
                )

        if len(cycles) > 1:
            st.subheader("Historical fundraising")
            hist = pd.DataFrame(cycles)
            hist["total_receipts"] = hist["total_receipts"].map(to_float)
            hist["pac_contributions"] = hist["pac_contributions"].map(to_float)
            hist = hist[["cycle", "total_receipts", "pac_contributions"]].set_index(
                "cycle"
            )
            st.line_chart(hist)

# ── Legislative record ─────────────────────────────────────────────────────────

with record_tab:
    record = get(f"/members/{key}/record")
    sponsored = record.get("sponsored", [])
    votes = record.get("votes", [])

    if not sponsored and not votes:
        st.caption("No legislative record found for this official.")

    if sponsored:
        st.subheader(f"Sponsored bills ({len(sponsored)})")
        sp_df = pd.DataFrame(sponsored)
        cols = [c for c in ["identifier", "title", "is_primary", "introduced_date"]
                if c in sp_df.columns]
        st.dataframe(
            sp_df[cols],
            hide_index=True,
            column_config={
                "identifier": "Bill",
                "title": "Title",
                "is_primary": "Primary sponsor",
                "introduced_date": "Introduced",
            },
            on_select="rerun",
            selection_mode="single-row",
        )

    if votes:
        st.subheader(f"Votes ({len(votes)})")
        vote_df = pd.DataFrame(votes)
        vote_cols = [c for c in
                     ["identifier", "title", "vote_option", "vote_date", "vote_result"]
                     if c in vote_df.columns]
        st.dataframe(
            vote_df[vote_cols],
            hide_index=True,
            column_config={
                "identifier": "Bill",
                "title": "Title",
                "vote_option": "Vote",
                "vote_date": "Date",
                "vote_result": "Result",
            },
        )

# ── Conflict of interest ───────────────────────────────────────────────────────

with conflict_tab:
    coi = get(f"/members/{key}/conflict")
    latest = coi.get("latest")

    if not latest:
        st.caption("No conflict of interest data available yet — FEC finance data needed.")
        st.stop()

    risk_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(
        latest["risk_level"], "⚪"
    )
    score = to_float(latest["coi_score"])
    st.metric(
        "Conflict of Interest Score",
        f"{score:.1f} / 100" if score is not None else "—",
        help=(
            "PAC dependency score: percentage of total fundraising from PACs and "
            "political committees. Higher scores indicate greater reliance on organized "
            "money vs. grassroots individual donors. 0–29 = Low · 30–59 = Medium · "
            "60–100 = High."
        ),
    )
    st.markdown(f"{risk_color} **{latest['risk_level']} risk**")

    st.markdown("#### What this means")
    st.info(latest["evidence_description"])

    if latest.get("regulated_industries") and latest.get("committees_served"):
        st.markdown("#### Committee oversight context")
        st.markdown(
            f"This official sits on committees that oversee: "
            f"**{latest['regulated_industries']}**"
        )
        st.caption(
            "A high COI score combined with committee oversight of industries that "
            "are major PAC donors warrants further scrutiny of voting record."
        )

    history = coi.get("history", [])
    if len(history) > 1:
        st.subheader("PAC dependency over time")
        hist_df = pd.DataFrame(history)[["cycle", "coi_score", "pac_contributions",
                                         "total_receipts"]]
        hist_df["coi_score"] = hist_df["coi_score"].map(to_float)
        hist_df["pac_contributions"] = hist_df["pac_contributions"].map(to_float)
        hist_df["total_receipts"] = hist_df["total_receipts"].map(to_float)
        st.line_chart(hist_df.set_index("cycle")["coi_score"])

        st.dataframe(
            hist_df,
            hide_index=True,
            column_config={
                "cycle": "Cycle",
                "coi_score": st.column_config.NumberColumn("COI Score", format="%.1f"),
                "pac_contributions": st.column_config.NumberColumn(
                    "PAC $", format="$%,.0f"
                ),
                "total_receipts": st.column_config.NumberColumn(
                    "Total raised", format="$%,.0f"
                ),
            },
        )
