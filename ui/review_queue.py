"""
REVIEW QUEUE (Team Lead) — replaces approving hundreds of scripts a day in WhatsApp.
Pick an intern → their pending scripts grouped by creator → edit inline →
approve / reject one, a creator's batch, or everything.
"""
import streamlit as st

import auth
import store
from deploy import add_log, deploy_batch
from ui import components as ui

SS = st.session_state


def _approve(ids, reviewer):
    # Save any inline edits before approving
    for i in ids:
        key = f"rq_edit_{i}"
        if key in SS:
            store.set_draft_content(i, SS[key])
    store.update_drafts(ids, reviewer=reviewer, status=store.APPROVED)
    add_log(f"Approved {len(ids)} script{'s' if len(ids) != 1 else ''}", "success")
    st.toast(f"Approved {len(ids)}")


def _reject(ids, reviewer):
    store.update_drafts(ids, reviewer=reviewer, status=store.REJECTED)
    add_log(f"Rejected {len(ids)} script{'s' if len(ids) != 1 else ''}", "error")
    st.toast(f"Rejected {len(ids)}")


def render(display_name):
    df = store.drafts()
    pending = df[df["status"] == store.PENDING]
    reviewed_today = df[(df["reviewed_at"].str[:10] == store.now_str()[:10]) & (df["status"] != store.PENDING)]

    ui.page_header("Review", "Queue", "EVERY SCRIPT YOUR INTERNS SUBMIT LANDS HERE — EDIT INLINE, APPROVE OR REJECT, NO WHATSAPP")
    ui.stat_strip([
        ("Pending", len(pending), "a", "awaiting your call"),
        ("Interns waiting", pending["intern"].nunique(), "c", "with open submissions"),
        ("Approved today", (reviewed_today["status"].isin([store.APPROVED, store.SHIPPED])).sum(), "g", "incl. shipped"),
        ("Rejected today", (reviewed_today["status"].isin([store.REJECTED, store.DISMISSED])).sum(), "r", "sent back"),
    ])
    ui.show_flash()

    interns = sorted(set(auth.interns()) | set(pending["intern"]))
    if SS.get("rq_intern") not in interns:
        with_work = [i for i in interns if (pending["intern"] == i).any()]
        SS.rq_intern = with_work[0] if with_work else (interns[0] if interns else None)

    side, main = st.columns([1, 3.2], gap="large")

    with side:
        ui.section("Interns")
        for name in interns:
            n = int((pending["intern"] == name).sum())
            active = name == SS.rq_intern
            if st.button(f"{name}   ·   {n}", key=f"rq_pick_{name}", width="stretch",
                         type="primary" if active else "secondary"):
                SS.rq_intern = name
                st.rerun()

    with main:
        if not SS.rq_intern:
            ui.empty("No interns configured", "Add interns in data/users.csv")
            return
        mine = pending[pending["intern"] == SS.rq_intern]
        if mine.empty:
            ui.empty(f"{SS.rq_intern} is all clear", "Nothing waiting for review")
            return

        top_l, top_r, top_r2 = st.columns([2, 1, 1.2])
        with top_l:
            ui.section(f"{SS.rq_intern} · {len(mine)} pending")
        with top_r:
            if st.button(f"APPROVE ALL {len(mine)}", key="rq_all", type="primary", width="stretch"):
                _approve(mine["id"].tolist(), display_name)
                st.rerun()
        with top_r2:
            if st.button(f"APPROVE + SHIP ALL {len(mine)}", key="rq_ship_all", width="stretch",
                         help="Approve and push straight to creator docs — skips the intern's inbox"):
                ids = mine["id"].tolist()
                _approve(ids, display_name)
                fresh = store.drafts()
                jobs = [{"creator": r["creator"], "content": r["content"], "format": r["format"],
                         "script_type": r["script_type"], "deploy_date": store.parse_date(r["deploy_date"]),
                         "draft_id": r["id"]} for _, r in fresh[fresh["id"].isin(ids)].iterrows()]
                ok, failures = deploy_batch(jobs, display_name)
                ui.flash("success", f"{ok} script{'s' if ok != 1 else ''} approved and shipped to creator docs.")
                for c, why in failures:
                    ui.flash("error", f"{c}: {why}")
                st.rerun()

        for creator, group in mine.groupby("creator", sort=False):
            with st.container(border=True):
                fmts = ", ".join(sorted(group["format"].unique()))
                ui.card_head(creator, f"{len(group)} SCRIPT{'S' if len(group) != 1 else ''} · {fmts}",
                             ui.badge("pending", "pending"))
                for _, r in group.iterrows():
                    meta = f"{r['format'].upper()} · {r['script_type'].upper()} · SUBMITTED {r['created_at'][11:]} · FOR {r['deploy_date']}"
                    st.markdown(f'<div class="syn-card-meta" style="margin:0.5rem 0 0.3rem">{meta}</div>',
                                unsafe_allow_html=True)
                    st.text_area("Script", value=r["content"], key=f"rq_edit_{r['id']}", height=220,
                                 label_visibility="collapsed")
                    b1, b2, _ = st.columns([1, 1, 2.5])
                    with b1:
                        if st.button("APPROVE", key=f"ok_{r['id']}", type="primary", width="stretch"):
                            _approve([r["id"]], display_name)
                            st.rerun()
                    with b2:
                        if st.button("REJECT", key=f"rej_{r['id']}", width="stretch"):
                            _reject([r["id"]], display_name)
                            st.rerun()
                if len(group) > 1:
                    if st.button(f"APPROVE ALL {len(group)} FOR {creator.upper()}", key=f"rq_c_{creator}", width="stretch"):
                        _approve(group["id"].tolist(), display_name)
                        st.rerun()

