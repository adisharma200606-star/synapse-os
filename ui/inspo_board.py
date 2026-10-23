"""INSPO BOARD — one shared place for every reel worth replicating."""
import datetime

import pandas as pd
import streamlit as st

import store
from ui import components as ui

STATUSES = ["Pending", "Approved", "Rejected", "Used"]


def render(display_name):
    df = store.inspirations()
    counts = df["Status"].value_counts()

    ui.page_header("Inspo", "Board", "DROP EVERY REEL WORTH REPLICATING HERE · TL APPROVES · INTERNS PULL FROM APPROVED")
    ui.stat_strip([
        ("Total", len(df), "c", "links on the board"),
        ("Approved", int(counts.get("Approved", 0)), "g", "ready to script"),
        ("Pending", int(counts.get("Pending", 0)), "a", "needs a look"),
        ("Used", int(counts.get("Used", 0)), "", "already scripted"),
    ])

    ui.section("Quick add")
    formats = list(store.load_formats().keys())
    with st.form("inspo_add", clear_on_submit=True, border=False):
        a, b, c = st.columns([3, 1.2, 0.8])
        with a:
            link = st.text_input("Link", placeholder="https://www.instagram.com/reel/…", label_visibility="collapsed")
        with b:
            fmt = st.selectbox("Format", ["—"] + formats, label_visibility="collapsed")
        with c:
            add = st.form_submit_button("ADD ROW", width="stretch")
    if add:
        if not link.strip().startswith("http"):
            st.warning("That doesn't look like a link.")
        else:
            row = pd.DataFrame([{"Date": datetime.date.today().strftime("%d %b"), "Inspiration Link": link.strip(),
                                 "Format": "" if fmt == "—" else fmt, "Status": "Pending", "Added By": display_name}])
            store.save_inspirations(pd.concat([row, df], ignore_index=True))
            st.toast("Added to the board")
            st.rerun()

    ui.section("Board")
    edited = st.data_editor(
        df, key="inspo_editor", num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Date": st.column_config.TextColumn(width="small"),
            "Inspiration Link": st.column_config.LinkColumn(width="large"),
            "Format": st.column_config.SelectboxColumn(options=formats, width="medium"),
            "Status": st.column_config.SelectboxColumn(options=STATUSES, width="small", required=True),
            "Added By": st.column_config.TextColumn(width="small", disabled=True),
        },
    )
    if st.button("SAVE CHANGES", type="primary"):
        store.save_inspirations(edited.fillna(""))
        st.toast("Board saved")
        st.rerun()
