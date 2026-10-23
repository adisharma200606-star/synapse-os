"""
WRITE & DEPLOY — the core loop.
Pick a format → the full script and today's assigned creators load themselves →
drop in the inspiration link → ship to every creator doc in one click.
"""
import datetime

import streamlit as st

import config
import store
import google_api
from auth import TEAM_LEAD
from deploy import add_log, deploy_batch
from ui import components as ui

SS = st.session_state
PLACEHOLDER = "[PASTE LINK]"


# ─────────────────────────────────────────────
# STATE HELPERS (run as widget callbacks)
# ─────────────────────────────────────────────
def _iteration_labels(fmt):
    n = len(store.load_formats()[fmt]["iterations"])
    return [f"Take {i}" for i in range(1, n + 1)]


def _fill(text):
    text = text.replace("{HASHTAGS}", config.BRAND_HASHTAGS)
    link = SS.get("wd_inspo", "").strip()
    return text.replace(PLACEHOLDER, link) if link else text


def load_script(reset_creators=True):
    formats = store.load_formats()
    fmt = SS.wd_format
    labels = _iteration_labels(fmt)
    take = SS.get("wd_iter") if SS.get("wd_iter") in labels else labels[0]
    SS.wd_iter = take
    SS.wd_editor = _fill(formats[fmt]["iterations"][labels.index(take)])
    SS.wd_type = formats[fmt]["script_type"]
    SS.wd_applied_link = SS.get("wd_inspo", "").strip()
    if reset_creators:
        mapping, _, _ = google_api.load_bifurcation(SS.wd_date.isoformat())
        known = store.load_creators()
        SS.wd_creators = [c for c in google_api.creators_for_format(mapping, fmt) if c in known]


def on_format_change():
    SS.wd_iter = None
    load_script(reset_creators=True)


def on_iter_change():
    if SS.get("wd_iter") is None:  # segmented control deselected → keep current take
        SS.wd_iter = _iteration_labels(SS.wd_format)[0]
    load_script(reset_creators=False)


def on_date_change():
    load_script(reset_creators=True)


def on_inspo_change():
    """Swap the link into the script wherever it currently sits."""
    new = SS.wd_inspo.strip()
    old = SS.get("wd_applied_link", "")
    text = SS.wd_editor
    if old and old in text:
        text = text.replace(old, new if new else PLACEHOLDER)
    elif new:
        text = text.replace(PLACEHOLDER, new)
    SS.wd_editor = text
    SS.wd_applied_link = new


# ─────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────
def render(user_role, display_name):
    formats = store.load_formats()
    creators = store.load_creators()
    fmt_names = list(formats.keys())
    is_tl = user_role == TEAM_LEAD

    if "wd_format" not in SS:
        SS.wd_format = fmt_names[0]
        SS.wd_date = datetime.date.today()
        SS.wd_inspo = ""
        load_script()

    ui.page_header(
        "Write &", "Deploy",
        "SELECT A FORMAT → SCRIPT + TODAY'S CREATORS LOAD AUTOMATICALLY → ADD INSPIRATION → SHIP"
        if is_tl else
        "SELECT A FORMAT → SCRIPT + TODAY'S CREATORS LOAD AUTOMATICALLY → ADD INSPIRATION → SUBMIT FOR REVIEW",
    )

    left, right = st.columns([2.3, 1], gap="large")

    with left:
        c1, c2, c3 = st.columns([1, 1.4, 1])
        with c1:
            ui.step(1, "Deploy date")
            st.date_input("Deploy date", key="wd_date", on_change=on_date_change,
                          format="DD/MM/YYYY", label_visibility="collapsed")
        with c2:
            ui.step(2, "Format")
            st.selectbox("Format", fmt_names, key="wd_format", on_change=on_format_change,
                         label_visibility="collapsed")
        with c3:
            ui.step("·", "Script type")
            st.selectbox("Script type", store.SCRIPT_TYPES, key="wd_type", label_visibility="collapsed")

        mapping, source, err = google_api.load_bifurcation(SS.wd_date.isoformat())
        assigned = google_api.creators_for_format(mapping, SS.wd_format)
        unknown = [c for c in assigned if c not in creators]
        if err:
            st.warning(f"Bifurcation: {err}")
        else:
            ui.hint(f"BIFURCATION · {source} → <b>{len(assigned)} creator{'s' if len(assigned) != 1 else ''}</b> "
                    f"assigned to {SS.wd_format} on {SS.wd_date.strftime('%d %b')}")
        if unknown:
            st.warning(f"In the sheet but not in your roster (data/links.csv): {', '.join(unknown)}")

        ui.step(3, "Inspiration link")
        st.text_input("Inspiration", key="wd_inspo", on_change=on_inspo_change,
                      placeholder="Paste the reel / TikTok / Short this script replicates",
                      label_visibility="collapsed")

        e1, e2 = st.columns([3, 1])
        with e1:
            ui.step(4, "Script")
        with e2:
            labels = _iteration_labels(SS.wd_format)
            if len(labels) > 1:
                st.segmented_control("Take", labels, key="wd_iter", on_change=on_iter_change,
                                     label_visibility="collapsed")
        st.text_area("Script", key="wd_editor", height=430, label_visibility="collapsed")
        txt = SS.wd_editor
        ui.hint(f"{len(txt)} CHARS · {len(txt.split())} WORDS · {txt.count(chr(10)) + 1} LINES")

        ui.step(5, "Creators")
        st.multiselect("Creators", list(creators.keys()), key="wd_creators", label_visibility="collapsed",
                       placeholder="Pick creators — today's bifurcation pre-fills this")

        targets = SS.wd_creators
        n = len(targets)
        if is_tl:
            label = f"SEND IT  →  DEPLOY TO {n} DOC{'S' if n != 1 else ''}"
            with st.container(key="cta_go"):
                go = st.button(label, width="stretch", disabled=n == 0)
        else:
            label = f"SUBMIT {n} SCRIPT{'S' if n != 1 else ''} FOR REVIEW"
            with st.container(key="cta_submit"):
                go = st.button(label, width="stretch", disabled=n == 0)

        if go:
            # Fill the placeholder here too, in case the link field's callback lost a race with the click
            text = _fill(SS.wd_editor).strip()
            if PLACEHOLDER in text:
                st.error("The script still has [PASTE LINK] in it — add the inspiration link in step 3 first.")
            elif not text:
                st.error("Script is empty.")
            elif is_tl:
                jobs = [{"creator": c, "content": text, "format": SS.wd_format, "script_type": SS.wd_type,
                         "deploy_date": SS.wd_date} for c in targets]
                ok, failures = deploy_batch(jobs, display_name)
                if ok:
                    st.success(f"{ok} script{'s' if ok != 1 else ''} live in creator docs under "
                               f"{config.doc_date_header(SS.wd_date)}.")
                    if config.is_live():
                        links = " · ".join(f"[{c} ↗]({creators[c]})" for c in targets if c not in dict(failures))
                        st.markdown(links)
                for c, why in failures:
                    st.error(f"{c}: {why}")
            else:
                count = store.add_drafts(display_name, targets, SS.wd_format, SS.wd_type, text, SS.wd_date)
                add_log(f"{count} × {SS.wd_format} submitted for review ({', '.join(targets)})", "warn")
                st.success(f"{count} script{'s' if count != 1 else ''} sent to the Team Lead's review queue.")
                st.toast("Submitted for review")

    with right:
        ui.section("Session")
        mine_today = store.scripts()
        today_count = (mine_today["deploy_date"] == datetime.date.today().isoformat()).sum()
        pending = (store.drafts()["status"] == store.PENDING).sum()
        st.markdown(
            f'<div class="syn-stat-strip" style="grid-template-columns:1fr 1fr;margin-bottom:1rem">'
            f'<div class="syn-stat hi"><div class="syn-stat-label">Shipped today</div><div class="syn-stat-value g">{today_count}</div></div>'
            f'<div class="syn-stat"><div class="syn-stat-label">Awaiting review</div><div class="syn-stat-value a">{pending}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        ui.section("Deploy log")
        ui.deploy_log()

        ui.section(f"Bifurcation · {SS.wd_date.strftime('%d %b')}")
        if mapping:
            rows = "".join(
                f'<div style="display:flex;justify-content:space-between;gap:1rem;padding:0.35rem 0;'
                f'border-bottom:1px solid var(--border-dim);font-family:var(--font-mono);font-size:0.62rem">'
                f'<span style="color:{"var(--accent-cyan)" if f == SS.wd_format else "var(--text-secondary)"}">{f}</span>'
                f'<span style="color:var(--text-dim);text-align:right">{", ".join(cs) or "—"}</span></div>'
                for f, cs in mapping.items()
            )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            ui.empty("No bifurcation", "Nothing assigned for this date")
