"""
Deploy orchestration — the money moment.
One function pushes a batch of scripts to creator docs with a live progress
bar, writes the audit trail, and narrates everything into the session log.
"""
import datetime

import streamlit as st

import store
import google_api


def add_log(msg, level="info"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.deploy_log.insert(0, (ts, msg, level))
    st.session_state.deploy_log = st.session_state.deploy_log[:80]


def deploy_batch(jobs, deployed_by):
    """
    jobs: list of dicts with creator, content, format, script_type, deploy_date, (optional) draft_id
    Returns (ok_count, failures[list of (creator, reason)])
    """
    creators = store.load_creators()
    bar = st.progress(0.0, text="Initialising deploy…")
    ok, failures, shipped_drafts = 0, [], []

    for i, job in enumerate(jobs, start=1):
        c = job["creator"]
        bar.progress((i - 1) / len(jobs), text=f"Deploying → {c}  ({i}/{len(jobs)})")
        success, msg = google_api.deploy_script(creators.get(c, ""), job["content"], job["deploy_date"])
        if success:
            ok += 1
            store.log_deploy(c, job["format"], job["script_type"], deployed_by, job["deploy_date"])
            add_log(f"{job['format']} → {c} · {msg}", "success")
            if job.get("draft_id"):
                shipped_drafts.append(job["draft_id"])
        else:
            failures.append((c, msg))
            add_log(f"{job['format']} → {c} FAILED · {msg}", "error")

    if shipped_drafts:
        store.update_drafts(shipped_drafts, status=store.SHIPPED)
    bar.progress(1.0, text=f"Done · {ok}/{len(jobs)} deployed")
    st.session_state.session_deploys += ok
    return ok, failures
