"""
Everything that talks to Google lives here.

LIVE mode  -> real Sheets / Docs API calls through the service account.
DEMO mode  -> same function signatures, local data, simulated deploys.
The UI never needs to know which mode it's in.
"""
import re
import csv
import time
import datetime

import streamlit as st

import config

DOC_ID_RE = re.compile(r"/d/([a-zA-Z0-9_-]{20,})")

# Labels that get bolded when a script lands in a creator's doc
BOLD_LABELS = [
    "Inspiration:", "Persistent Hook:", "Hook 1:", "Hook 2:", "Hook 3:",
    "Dialogue:", "Caption:", "Audio:", "Expression:", "Video Guidelines:",
]


def doc_id_from_url(url):
    m = DOC_ID_RE.search(url or "")
    return m.group(1) if m else None


def _service(api, version):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, scopes=config.SCOPES
    )
    return build(api, version, credentials=creds, cache_discovery=False)


# ─────────────────────────────────────────────
# BIFURCATION
# ─────────────────────────────────────────────
def _demo_bifurcation_rows():
    with open(config.BIFURCATION_DEMO, "r", encoding="utf-8") as f:
        return list(csv.reader(f))


@st.cache_data(ttl=300, show_spinner=False)
def load_bifurcation(date_iso):
    """
    Returns (mapping, source, error)
      mapping : {format_name: [creator, ...]}
      source  : human label of where it came from
      error   : string or None
    """
    target = datetime.date.fromisoformat(date_iso)

    if config.is_live() and config.BIFURCATION_SHEET_ID:
        try:
            sheets = _service("sheets", "v4")
            meta = sheets.spreadsheets().get(spreadsheetId=config.BIFURCATION_SHEET_ID).execute()
            tabs = [s["properties"]["title"] for s in meta["sheets"]]
            tab = config.resolve_today_tab(tabs, target)
            if not tab:
                return {}, "Google Sheet", f"No date tab found. Tabs: {tabs}"
            values = sheets.spreadsheets().values().get(
                spreadsheetId=config.BIFURCATION_SHEET_ID, range=f"'{tab}'"
            ).execute().get("values", [])
            mapping = config.parse_bifurcation_rows(values)
            if not mapping:
                return {}, f"Sheet · {tab}", "Couldn't find a header row in that tab"
            return mapping, f"Sheet · {tab}", None
        except Exception as e:
            msg = str(e)
            if "operation is not supported" in msg.lower():
                msg = "That file is an uploaded .xlsx, not a native Google Sheet. Open it → File → Save as Google Sheets, then use the new ID."
            elif "403" in msg or "permission" in msg.lower():
                msg = f"No access. Share the sheet with {config.service_account_email()}"
            return {}, "Google Sheet", msg

    try:
        return config.parse_bifurcation_rows(_demo_bifurcation_rows()), "Demo sheet", None
    except FileNotFoundError:
        return {}, "Demo sheet", "data/bifurcation_demo.csv is missing"


def creators_for_format(mapping, format_name):
    """Fuzzy column match: 'Street quiz' matches 'Street Quiz 2.0' etc."""
    key = format_name.lower().strip()
    for h, creators in mapping.items():
        if h.lower().strip() == key:
            return creators
    for h, creators in mapping.items():
        hl = h.lower().strip()
        if key in hl or hl in key:
            return creators
    return []


# ─────────────────────────────────────────────
# DEPLOY
# ─────────────────────────────────────────────
def _u16(s):
    """Google Docs counts positions in UTF-16 units (emoji = 2), not Python characters."""
    return len(s.encode("utf-16-le")) // 2


def _build_requests(text, date_header):
    top_sep = "\n"
    body = date_header + "\n\n" + text.strip() + "\n"
    payload = top_sep + body + "\n"

    reqs = [{"insertText": {"location": {"index": 1}, "text": payload}}]

    body_start = 1 + _u16(top_sep)
    body_end = body_start + _u16(body)
    reqs.append({"updateParagraphStyle": {
        "range": {"startIndex": body_start, "endIndex": body_end},
        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        "fields": "namedStyleType"}})
    reqs.append({"updateParagraphStyle": {
        "range": {"startIndex": body_start, "endIndex": body_start + _u16(date_header)},
        "paragraphStyle": {"namedStyleType": "HEADING_2"},
        "fields": "namedStyleType"}})

    rule = {
        "color": {"color": {"rgbColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}},
        "width": {"magnitude": 1, "unit": "PT"},
        "padding": {"magnitude": 1, "unit": "PT"},
        "dashStyle": "SOLID",
    }
    reqs.append({"updateParagraphStyle": {
        "range": {"startIndex": body_end, "endIndex": body_end + 1},
        "paragraphStyle": {"borderBottom": rule},
        "fields": "borderBottom"}})

    url_re = re.compile(r"https?://[^\s)\]]+")
    cur = 1
    for line in payload.split("\n"):
        def span(a, b):
            return {"startIndex": cur + _u16(line[:a]), "endIndex": cur + _u16(line[:b])}
        for kw in BOLD_LABELS:
            pos = line.find(kw)
            if pos != -1:
                reqs.append({"updateTextStyle": {"range": span(pos, pos + len(kw)),
                                                 "textStyle": {"bold": True}, "fields": "bold"}})
        if "FINAL NOTE" in line.upper():
            reqs.append({"updateTextStyle": {"range": span(0, len(line)),
                                             "textStyle": {"italic": True}, "fields": "italic"}})
        for m in url_re.finditer(line):
            reqs.append({"updateTextStyle": {"range": span(m.start(), m.end()),
                                             "textStyle": {"link": {"url": m.group(0)}, "underline": True},
                                             "fields": "link,underline"}})
        cur += _u16(line) + 1
    return reqs


def deploy_script(doc_url, text, deploy_date):
    """
    Pushes one script to the top of one creator's Google Doc.
    Returns (ok: bool, message: str).
    """
    header = config.doc_date_header(deploy_date)

    if not config.is_live():
        time.sleep(0.35)  # feel like a network call in demo recordings
        return True, "simulated (demo mode)"

    doc_id = doc_id_from_url(doc_url)
    if not doc_id:
        return False, "no valid Google Doc link for this creator"
    try:
        _service("docs", "v1").documents().batchUpdate(
            documentId=doc_id, body={"requests": _build_requests(text, header)}
        ).execute()
        return True, "deployed"
    except Exception as e:
        msg = str(e)
        if "403" in msg or "permission" in msg.lower():
            return False, f"no access — share the doc with {config.service_account_email()} as Editor"
        if "404" in msg:
            return False, "doc not found — check the link in data/links.csv"
        return False, msg[:160]


def check_doc_access(doc_url):
    """Used by seed_demo.py. Returns (ok, title_or_error)."""
    doc_id = doc_id_from_url(doc_url)
    if not doc_id:
        return False, "not a Google Doc link"
    try:
        doc = _service("docs", "v1").documents().get(documentId=doc_id).execute()
        return True, doc.get("title", "")
    except Exception as e:
        return False, str(e)[:120]
