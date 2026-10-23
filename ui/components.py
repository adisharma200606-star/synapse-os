"""Small shared UI pieces so every page looks like the same product."""
import html

import streamlit as st


def page_header(title, accent, desc):
    st.markdown(
        f'<div class="syn-page-header"><div class="syn-page-title">{title} <span>{accent}</span></div>'
        f'<div class="syn-page-desc">{desc}</div></div>',
        unsafe_allow_html=True,
    )


def stat_strip(stats):
    """stats: list of (label, value, color_class, sub). color_class in '', g, c, a, r"""
    cells = "".join(
        f'<div class="syn-stat{" hi" if i == 0 else ""}"><div class="syn-stat-label">{lbl}</div>'
        f'<div class="syn-stat-value {cls}">{val}</div><div class="syn-stat-sub">{sub}</div></div>'
        for i, (lbl, val, cls, sub) in enumerate(stats)
    )
    st.markdown(f'<div class="syn-stat-strip">{cells}</div>', unsafe_allow_html=True)


def section(label):
    st.markdown(f'<div class="syn-section">{label}</div>', unsafe_allow_html=True)


def step(n, label):
    st.markdown(f'<div class="syn-step"><span class="syn-step-num">{n}</span>{label}</div>', unsafe_allow_html=True)


def hint(text):
    st.markdown(f'<div class="syn-hint">{text}</div>', unsafe_allow_html=True)


def empty(label, sub=""):
    st.markdown(
        f'<div class="syn-empty"><div class="syn-empty-label">{label}</div>'
        f'<div class="syn-empty-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def badge(text, kind="neutral"):
    return f'<span class="syn-badge {kind}">{html.escape(text)}</span>'


def card_head(title, meta="", right=""):
    st.markdown(
        f'<div class="syn-card-head"><div><div class="syn-card-title">{html.escape(title)}</div>'
        f'<div class="syn-card-meta">{meta}</div></div><div>{right}</div></div>',
        unsafe_allow_html=True,
    )


def script_preview(text):
    body = html.escape(text).replace("\n", "<br>")
    st.markdown(f'<div class="syn-script-preview">{body}</div>', unsafe_allow_html=True)


def deploy_log():
    rows = st.session_state.get("deploy_log", [])
    if not rows:
        body = '<span class="log-dim">// awaiting first deploy…</span>'
    else:
        body = "<br>".join(
            f'<span class="log-ts">{ts}</span><span class="log-{lvl}">{html.escape(msg)}</span>' for ts, msg, lvl in rows
        )
    st.markdown(f'<div class="syn-log">{body}</div>', unsafe_allow_html=True)


def flash(kind, msg):
    """Queue a message that survives the next st.rerun()."""
    st.session_state.setdefault("flash", []).append((kind, msg))


def show_flash():
    for kind, msg in st.session_state.pop("flash", []):
        getattr(st, kind)(msg)
