"""
SYNAPSE // OS — central configuration.

Everything you might want to change lives in config.json (not in code):
  - bifurcation_sheet_id : Google Sheet that says which creator gets which format today
  - brand_hashtags       : caption hashtags dropped into every script
  - org_name             : shown on the login screen

If credentials.json exists next to this file, Synapse runs in LIVE mode
(real Google Docs / Sheets). Without it, Synapse runs in DEMO mode:
deploys are simulated and the bifurcation comes from data/bifurcation_demo.csv.
"""
import os
import json
import re
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── FILES ──
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
CONFIG_FILE      = os.path.join(BASE_DIR, "config.json")
STYLES_FILE      = os.path.join(BASE_DIR, "styles.css")

LINKS_FILE       = os.path.join(DATA_DIR, "links.csv")
SOCIALS_FILE     = os.path.join(DATA_DIR, "socials.csv")
USERS_FILE       = os.path.join(DATA_DIR, "users.csv")
FORMATS_FILE     = os.path.join(DATA_DIR, "formats.json")
BIFURCATION_DEMO = os.path.join(DATA_DIR, "bifurcation_demo.csv")
DRAFTS_DB        = os.path.join(DATA_DIR, "drafts_db.csv")
SCRIPTS_DB       = os.path.join(DATA_DIR, "scripts_db.csv")
INSPO_DB         = os.path.join(DATA_DIR, "inspirations_db.csv")
PERFORMANCE_DB   = os.path.join(DATA_DIR, "performance.csv")

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

VERSION = "v3.0"


# ── CONFIG.JSON ──
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(updates):
    cfg = load_config()
    cfg.update(updates)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


_cfg = load_config()
BIFURCATION_SHEET_ID = _cfg.get("bifurcation_sheet_id", "").strip()
BRAND_HASHTAGS       = _cfg.get("brand_hashtags", "#loqui #learnwithloqui")
ORG_NAME             = _cfg.get("org_name", "Loqui · Creator Content Ops")


def is_live():
    """LIVE = we have a Google service-account key on disk."""
    return os.path.exists(CREDENTIALS_FILE)


def service_account_email():
    if not is_live():
        return ""
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("client_email", "")
    except Exception:
        return ""


# ── DATES ──
def ordinal(n):
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def doc_date_header(d):
    """The heading written into creator docs, e.g. OCTOBER 22, 2026."""
    return d.strftime("%B %d, %Y").upper()


def resolve_today_tab(tab_names, target_date=None):
    """
    Picks the bifurcation tab for a given day.
      1. Exact match for the date (or the day before) in any common format
      2. Most recent YYYY-MM-DD tab
      3. Last tab whose name looks like a date ('13th March')
    Never falls back to a non-date tab.
    """
    d = target_date or datetime.date.today()

    def candidates(day):
        return [
            day.strftime("%Y-%m-%d"),
            f"{ordinal(day.day)} {day.strftime('%B')}",
            f"{ordinal(day.day)} {day.strftime('%b')}",
            f"{day.day} {day.strftime('%B')}",
            f"{day.day} {day.strftime('%b')}",
            day.strftime("%d %b"),
            day.strftime("%d/%m"),
        ]

    lowered = {t.lower().strip(): t for t in tab_names}
    for delta in (0, 1):
        for c in candidates(d - datetime.timedelta(days=delta)):
            if c.lower() in lowered:
                return lowered[c.lower()]

    iso = []
    for t in tab_names:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})$", t.strip())
        if m:
            try:
                iso.append((datetime.date.fromisoformat(m.group(1)), t))
            except ValueError:
                pass
    if iso:
        return max(iso)[1]

    months = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    date_like = [t for t in tab_names if any(m in t.lower() for m in months) and any(ch.isdigit() for ch in t)]
    return date_like[-1] if date_like else None


def parse_bifurcation_rows(rows):
    """
    Turns raw sheet rows into {format_name: [creators]}.
    Real sheets often have empty rows above the header, so the header is
    auto-detected: the first row with 3+ non-empty cells whose first
    non-empty cell doesn't start with a digit.
    """
    header_idx = None
    for i, row in enumerate(rows):
        cells = [str(c).strip() for c in row if str(c).strip()]
        if len(cells) >= 3 and not cells[0][0].isdigit():
            header_idx = i
            break
    if header_idx is None:
        return {}

    headers = [str(h).strip() for h in rows[header_idx]]
    result = {h: [] for h in headers if h}
    for row in rows[header_idx + 1:]:
        for col, h in enumerate(headers):
            if not h or col >= len(row):
                continue
            val = str(row[col]).strip()
            if val and val.lower() != "nan":
                result[h].append(val)
    return result
