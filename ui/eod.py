"""EOD REPORT — assigned vs shipped, per creator, in one screenshot."""
import datetime

import pandas as pd
import streamlit as st

import store
import google_api
from ui import components as ui


def render(display_name):
    creators = store.load_creators()

    ui.page_header("EOD", "Report", "WHAT WAS ASSIGNED IN THE BIFURCATION VS WHAT ACTUALLY SHIPPED · SCREENSHOT-READY")

    a, b = st.columns([1, 3])
    with a:
        day = st.date_input("Report date", value=datetime.date.today(), key="eod_date", format="DD/MM/YYYY")
    mapping, source, err = google_api.load_bifurcation(day.isoformat())
    if err:
        st.warning(f"Bifurcation: {err}")

    assigned = {}
    for fmt, cs in mapping.items():
        for c in cs:
            assigned.setdefault(c, []).append(fmt)

    with b:
        default = [c for c in creators if c in assigned]
        picked = st.multiselect("Creators you worked on", list(creators.keys()), default=default, key=f"eod_pick_{day}")

    if not picked:
        ui.empty("Pick at least one creator")
        return

    log = store.scripts()
    day_log = log[(log["deploy_date"] == day.isoformat()) & (log["result"] == "SHIPPED")]
    rows = []
    for c in picked:
        fmts = assigned.get(c, [])
        done = int((day_log["creator"] == c).sum())
        target = len(fmts)
        status = "Done" if target and done >= target else ("Partial" if done else ("—" if not target else "Not started"))
        rows.append({"Creator": c, "Assigned": target, "Shipped": done, "Formats": ", ".join(fmts) or "—", "Status": status})
    table = pd.DataFrame(rows)

    total_a, total_s = int(table["Assigned"].sum()), int(table["Shipped"].sum())
    st.markdown(
        f'<div class="syn-banner"><div class="syn-banner-date">{day.strftime("%A, %d %B %Y")}</div>'
        f'<div class="syn-banner-total">{total_s} / {total_a} SHIPPED · {len(picked)} CREATORS · {source.upper()}</div></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        table, width="stretch", hide_index=True,
        column_config={
            "Shipped": st.column_config.ProgressColumn(
                "Shipped", min_value=0, max_value=max(int(table["Assigned"].max()), int(table["Shipped"].max()), 1),
                format="%d"),
        },
    )

    with st.expander("WhatsApp-ready EOD"):
        lines = [f"*EOD — {display_name} — {day.strftime('%d %b')}*", f"Shipped {total_s}/{total_a}", ""]
        lines += [f"• {r['Creator']}: {r['Shipped']}/{r['Assigned']} ({r['Formats']})" for r in rows]
        st.code("\n".join(lines), language=None)
