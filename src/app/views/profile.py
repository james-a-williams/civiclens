import pandas as pd
import streamlit as st
from api_client import get, to_float

key = st.session_state.get("candidacy_key")
if not key:
    st.info("Pick a candidate from **Find Candidates** to see their profile.")
    st.stop()

profile = get(f"/candidates/{key}")

badge = {"federal": "🟦 Federal", "state": "🟨 State", "local": "🟩 Local"}[profile["level"]]
st.title(profile["display_name"])
race = " · ".join(
    str(part)
    for part in [
        badge,
        profile["office"],
        profile["state"],
        f"District {profile['district']}" if profile["district"] is not None else None,
        profile["cycle"],
    ]
    if part is not None
)
st.caption(race)
if profile["party"]:
    st.markdown(f"**Party:** {profile['party']}")
if profile["is_incumbent"]:
    st.markdown("✅ **Incumbent**")

overview_tab, finance_tab = st.tabs(["Overview", "Finance"])

with overview_tab:
    district = profile.get("district_context")
    if district:
        st.subheader(f"District context — {district['name']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Population", f"{district['total_population']:,}")
        m2.metric("Median household income", f"${district['median_household_income']:,}")
        if district["pct_bachelors"] is not None:
            m3.metric("Bachelor's degree+", f"{float(district['pct_bachelors']):.0%}")
        if district["pct_insured"] is not None:
            m4.metric("Health insured", f"{float(district['pct_insured']):.0%}")

        race_rows = {
            "White": district["pct_white"],
            "Black": district["pct_black"],
            "Hispanic/Latino": district["pct_hispanic"],
        }
        race_df = pd.DataFrame(
            {"share": [float(v) for v in race_rows.values() if v is not None]},
            index=[k for k, v in race_rows.items() if v is not None],
        )
        st.bar_chart(race_df, horizontal=True)
    else:
        st.caption("No district demographics available for this race.")

    if profile["other_candidacies"]:
        st.subheader("Other campaigns")
        st.dataframe(pd.DataFrame(profile["other_candidacies"]), hide_index=True)

with finance_tab:
    finance = get(f"/candidates/{key}/finance")
    summary = finance["summary"]
    if not summary:
        st.caption("No campaign finance filings found for this candidacy.")
        st.stop()

    source_label = {
        "fec": "Federal Election Commission",
        "ny_boe": "NY State Board of Elections (public financing program)",
        "nyc_cfb": "NYC Campaign Finance Board",
    }[summary["coverage"]]
    st.caption(f"Source: {source_label}")

    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        ("Total raised", summary["total_raised"]),
        ("Total spent", summary["total_spent"]),
        ("Cash on hand", summary["cash_on_hand"]),
        ("Public funds", summary["public_funds_received"]),
    ]
    for col, (label, value) in zip([m1, m2, m3, m4], metrics):
        value = to_float(value)
        col.metric(label, "—" if value is None else f"${value:,.0f}")

    if summary["contribution_count"]:
        d1, d2, d3 = st.columns(3)
        d1.metric("Contributions", f"{summary['contribution_count']:,}")
        d2.metric("Unique donors", f"{summary['unique_donor_count']:,}")
        small = to_float(summary["pct_small_dollar"])
        d3.metric("Small-dollar share (<$200)", "—" if small is None else f"{small:.0%}")

    if finance["top_donors"]:
        st.subheader("Top donors")
        donors = pd.DataFrame(finance["top_donors"])
        donors["total_amount"] = donors["total_amount"].map(to_float)
        st.dataframe(
            donors,
            hide_index=True,
            column_config={
                "contributor_name": "Donor",
                "employer_name": "Employer",
                "city": "City",
                "state": "State",
                "total_amount": st.column_config.NumberColumn("Total", format="$%,.0f"),
                "contribution_count": "Gifts",
            },
        )

    chart_col, geo_col = st.columns(2)
    if finance["top_employers"]:
        with chart_col:
            st.subheader("Top employers")
            employers = pd.DataFrame(finance["top_employers"]).set_index("employer_name")
            employers["total_amount"] = employers["total_amount"].map(to_float)
            st.bar_chart(employers["total_amount"], horizontal=True)
    if finance["geo_breakdown"]:
        with geo_col:
            st.subheader("Where the money comes from")
            geo = pd.DataFrame(finance["geo_breakdown"])
            geo["total_amount"] = geo["total_amount"].map(to_float)
            geo["place"] = geo["city"].str.title() + ", " + geo["state"].fillna("")
            st.bar_chart(geo.set_index("place")["total_amount"], horizontal=True)
