"""
MY INBOX (Intern) — what came back from the Team Lead.
Approved → publish to creator docs. Rejected → acknowledge and move on.
"""
import streamlit as st

import store
from deploy import deploy_batch
from ui import components as ui


def _jobs(rows):
    return [{"creator": r["creator"], "content": r["content"], "format": r["format"],
             "script_type": r["script_type"], "deploy_date": store.parse_date(r["deploy_date"]),
             "draft_id": r["id"]} for _, r in rows.iterrows()]


def render(display_name):
    df = store.drafts()
    mine = df[df["intern"] == display_name]
    approved = mine[mine["status"] == store.APPROVED]
    rejected = mine[mine["status"] == store.REJECTED]
    pending = mine[mine["status"] == store.PENDING]
    shipped = mine[mine["status"] == store.SHIPPED]

    ui.page_header("My", "Inbox", "APPROVED SCRIPTS ARE READY TO PUBLISH · REJECTED ONES NEED A SECOND LOOK")
    ui.stat_strip([
        ("Ready to publish", len(approved), "g", "approved by TL"),
        ("Awaiting review", len(pending), "a", "in the TL's queue"),
        ("Rejected", len(rejected), "r", "acknowledge to clear"),
        ("Shipped", len(shipped), "c", "all time"),
    ])
    ui.show_flash()

    ui.section(f"Approved · {len(approved)}")
    if approved.empty:
        ui.empty("Nothing approved yet", "Scripts appear here once the Team Lead signs off")
    else:
        if len(approved) > 1:
            with st.container(key="cta_go"):
                if st.button(f"PUBLISH ALL {len(approved)} TO GOOGLE DOCS", key="ib_all", width="stretch"):
                    ok, failures = deploy_batch(_jobs(approved), display_name)
                    ui.flash("success", f"{ok} script{'s' if ok != 1 else ''} published.")
                    for c, why in failures:
                        ui.flash("error", f"{c}: {why}")
                    st.rerun()
        for _, r in approved.iterrows():
            with st.container(border=True):
                ui.card_head(r["creator"], f"{r['format'].upper()} · APPROVED BY {r['reviewed_by'].upper()} · {r['reviewed_at'][11:]}",
                             ui.badge("approved", "approved"))
                with st.expander("View script"):
                    ui.script_preview(r["content"])
                if st.button(f"PUBLISH TO {r['creator'].upper()}'S DOC", key=f"pub_{r['id']}", type="primary", width="stretch"):
                    ok, failures = deploy_batch(_jobs(approved[approved["id"] == r["id"]]), display_name)
                    if ok:
                        ui.flash("success", f"Live in {r['creator']}'s doc.")
                    for c, why in failures:
                        ui.flash("error", f"{c}: {why}")
                    st.rerun()

    ui.section(f"Rejected · {len(rejected)}")
    if rejected.empty:
        ui.empty("No rejections", "Clean sheet")
    else:
        for _, r in rejected.iterrows():
            with st.container(border=True):
                ui.card_head(r["creator"], f"{r['format'].upper()} · REJECTED BY {r['reviewed_by'].upper()} · {r['reviewed_at'][11:]}",
                             ui.badge("rejected", "rejected"))
                ui.script_preview(r["content"])
                if st.button("ACKNOWLEDGE & DISMISS", key=f"ack_{r['id']}", width="stretch"):
                    store.update_drafts([r["id"]], status=store.DISMISSED)
                    st.rerun()

    if not pending.empty:
        ui.section(f"Waiting on the Team Lead · {len(pending)}")
        for _, r in pending.iterrows():
            st.markdown(
                f'<div class="syn-card-meta" style="padding:0.4rem 0;border-bottom:1px solid var(--border-dim)">'
                f'{r["creator"].upper()} · {r["format"].upper()} · SUBMITTED {r["created_at"]} &nbsp; {ui.badge("pending", "pending")}</div>',
                unsafe_allow_html=True,
            )
