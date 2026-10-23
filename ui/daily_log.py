"""DAILY LOG — the audit trail that never existed when everything ran on WhatsApp."""
import datetime

import altair as alt
import pandas as pd
import streamlit as st

import store
from ui import components as ui

CYAN, DIM, GRID = "#00D4FF", "#555D7A", "#222638"
MINUTES_SAVED_PER_DEPLOY = 1  # open doc → new heading → paste → format, done by hand


def _bar(df, x, y, horizontal=False, height=240):
    enc_x = alt.X(f"{x}:N", sort=None, axis=alt.Axis(labelColor=DIM, title=None, labelAngle=0, domainColor=GRID, tickColor=GRID))
    enc_y = alt.Y(f"{y}:Q", axis=alt.Axis(labelColor=DIM, title=None, gridColor=GRID, domainColor=GRID, tickColor=GRID))
    if horizontal:
        enc_x, enc_y = (alt.X(f"{y}:Q", axis=alt.Axis(labelColor=DIM, title=None, gridColor=GRID, domainColor=GRID)),
                        alt.Y(f"{x}:N", sort="-x", axis=alt.Axis(labelColor=DIM, title=None, domainColor=GRID)))
    return (alt.Chart(df).mark_bar(color=CYAN, cornerRadius=0, opacity=0.85)
            .encode(x=enc_x, y=enc_y, tooltip=[x, y])
            .properties(height=height, background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelFont="monospace", labelFontSize=10))


def render(display_name):
    log = store.scripts()
    today = datetime.date.today()
    shipped = log[log["result"] == "SHIPPED"]
    today_rows = shipped[shipped["deploy_date"] == today.isoformat()]
    minutes = len(shipped) * MINUTES_SAVED_PER_DEPLOY

    ui.page_header("Daily", "Log", "EVERY SCRIPT THAT LANDED IN A CREATOR DOC · WHO SHIPPED IT · WHEN · WHAT'S PERFORMING")
    ui.stat_strip([
        ("Scripts shipped", len(shipped), "c", "all time"),
        ("Shipped today", len(today_rows), "g", today.strftime("%d %b")),
        ("Creators active", shipped["creator"].nunique(), "", "received ≥1 script"),
        ("Hours saved", f"{minutes / 60:.1f}", "a", "vs. manual copy-paste"),
    ])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        ui.section("Shipped per day · last 14 days")
        days = [(today - datetime.timedelta(days=i)) for i in range(13, -1, -1)]
        per_day = shipped["deploy_date"].value_counts()
        trend = pd.DataFrame({"Day": [d.strftime("%d %b") for d in days],
                              "Scripts": [int(per_day.get(d.isoformat(), 0)) for d in days]})
        st.altair_chart(_bar(trend, "Day", "Scripts"), width="stretch", theme=None)
    with c2:
        ui.section("Distribution by format")
        dist = shipped["format"].value_counts().rename_axis("Format").reset_index(name="Scripts")
        if dist.empty:
            ui.empty("No data yet")
        else:
            st.altair_chart(_bar(dist, "Format", "Scripts", horizontal=True), width="stretch", theme=None)

    ui.section("Creator performance tracker")
    perf = store.performance()
    edited = st.data_editor(
        perf, key="perf_editor", num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Views": st.column_config.NumberColumn(format="localized", min_value=0),
            "Platform": st.column_config.SelectboxColumn(options=["Instagram", "TikTok", "YT Shorts"]),
            "Format": st.column_config.SelectboxColumn(options=list(store.load_formats().keys())),
            "Milestone URL": st.column_config.LinkColumn(),
        },
    )
    s1, s2 = st.columns([1, 3])
    with s1:
        if st.button("SAVE TRACKER", type="primary", width="stretch"):
            store.save_performance(edited.fillna(""))
            st.toast("Tracker saved")
            st.rerun()

    with st.expander("WhatsApp report — copy and paste into the group"):
        top = edited.sort_values("Views", ascending=False).head(5)
        lines = [f"*CONTENT UPDATE — {today.strftime('%d %b %Y').upper()}*", "",
                 f"*Shipped today:* {len(today_rows)} scripts across {today_rows['creator'].nunique()} creators", ""]
        if not today_rows.empty:
            for f, n in today_rows["format"].value_counts().items():
                lines.append(f"• {f}: {n}")
            lines.append("")
        if not top.empty:
            lines.append("*Top performers*")
            for _, r in top.iterrows():
                lines.append(f"• {r['Creator']} — {int(r['Views']):,} views on {r['Platform']} ({r['Format']})")
        st.code("\n".join(lines), language=None)

    ui.section("Archived deploy log")
    st.dataframe(log.iloc[::-1], width="stretch", hide_index=True, height=320,
                 column_config={"deployed_at": "Deployed at", "deploy_date": "Doc date", "creator": "Creator",
                                "format": "Format", "script_type": "Type", "deployed_by": "By", "result": "Result"})
