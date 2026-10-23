"""
Local data layer. Plain CSV files in data/ — swap for a real database later
without touching the UI, because every page goes through these functions.
"""
import os
import csv
import json
import uuid
import random
import datetime

import pandas as pd
import streamlit as st

import config

DRAFT_COLS = ["id", "created_at", "intern", "creator", "format", "script_type",
              "content", "status", "reviewed_at", "reviewed_by", "deploy_date"]
SCRIPT_COLS = ["deployed_at", "deploy_date", "creator", "format", "script_type", "deployed_by", "result"]
INSPO_COLS = ["Date", "Inspiration Link", "Format", "Status", "Added By"]
PERF_COLS = ["Creator", "Top Content", "Views", "Platform", "Format", "Milestone URL"]

SCRIPT_TYPES = ["Study", "Entertain", "Motivate", "Generic"]

# Draft statuses
PENDING, APPROVED, REJECTED, SHIPPED, DISMISSED = "PENDING", "APPROVED", "REJECTED", "SHIPPED", "DISMISSED"


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _read(path, cols):
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


def _write(df, path):
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)


# ─────────────────────────────────────────────
# REFERENCE DATA (creators, users, formats)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_creators():
    """{creator_name: google_doc_url}"""
    mapping = {}
    if not os.path.exists(config.LINKS_FILE):
        return mapping
    with open(config.LINKS_FILE, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            name, url = row[0].strip(), row[1].strip()
            if name and name.lower() not in ("creator", "name"):
                mapping[name] = url
    return mapping


@st.cache_data(ttl=300, show_spinner=False)
def load_socials(creator):
    if not os.path.exists(config.SOCIALS_FILE):
        return []
    df = pd.read_csv(config.SOCIALS_FILE, dtype=str, keep_default_na=False)
    rows = df[df["Creator"].str.strip().str.lower() == creator.strip().lower()]
    return [(r["Platform"].upper(), r["Account Link"]) for _, r in rows.iterrows() if r["Account Link"]]


@st.cache_data(ttl=300, show_spinner=False)
def load_users():
    if not os.path.exists(config.USERS_FILE):
        return [
            {"username": "tl1", "password": "tl123", "role": "TEAM LEAD", "display_name": "Team Lead"},
            {"username": "intern1", "password": "pass1", "role": "INTERN", "display_name": "Intern 1"},
        ]
    return pd.read_csv(config.USERS_FILE, dtype=str, keep_default_na=False).to_dict("records")


@st.cache_data(ttl=300, show_spinner=False)
def load_formats():
    """{format_name: {"script_type": str, "iterations": [str, ...]}}"""
    with open(config.FORMATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# DRAFTS (intern → TL review → intern publishes)
# ─────────────────────────────────────────────
def drafts():
    return _read(config.DRAFTS_DB, DRAFT_COLS)


def add_drafts(intern, creators, fmt, script_type, content, deploy_date):
    df = drafts()
    new = pd.DataFrame([{
        "id": uuid.uuid4().hex[:8], "created_at": now_str(), "intern": intern,
        "creator": c, "format": fmt, "script_type": script_type, "content": content,
        "status": PENDING, "reviewed_at": "", "reviewed_by": "", "deploy_date": deploy_date.isoformat(),
    } for c in creators])
    _write(pd.concat([df, new], ignore_index=True), config.DRAFTS_DB)
    return len(new)


def update_drafts(ids, reviewer=None, **fields):
    df = drafts()
    mask = df["id"].isin(ids)
    for k, v in fields.items():
        df.loc[mask, k] = v
    if reviewer:
        df.loc[mask, "reviewed_by"] = reviewer
        df.loc[mask, "reviewed_at"] = now_str()
    _write(df, config.DRAFTS_DB)


def set_draft_content(draft_id, content):
    df = drafts()
    df.loc[df["id"] == draft_id, "content"] = content
    _write(df, config.DRAFTS_DB)


# ─────────────────────────────────────────────
# DEPLOY LOG (every script that actually landed in a creator doc)
# ─────────────────────────────────────────────
def scripts():
    return _read(config.SCRIPTS_DB, SCRIPT_COLS)


def log_deploy(creator, fmt, script_type, deployed_by, deploy_date, result="SHIPPED"):
    df = scripts()
    row = pd.DataFrame([{
        "deployed_at": now_str(), "deploy_date": deploy_date.isoformat(), "creator": creator,
        "format": fmt, "script_type": script_type, "deployed_by": deployed_by, "result": result,
    }])
    _write(pd.concat([df, row], ignore_index=True), config.SCRIPTS_DB)


# ─────────────────────────────────────────────
# INSPO BOARD + PERFORMANCE
# ─────────────────────────────────────────────
def inspirations():
    return _read(config.INSPO_DB, INSPO_COLS)


def save_inspirations(df):
    _write(df[INSPO_COLS], config.INSPO_DB)


def performance():
    df = _read(config.PERFORMANCE_DB, PERF_COLS)
    df["Views"] = pd.to_numeric(df["Views"], errors="coerce").fillna(0).astype(int)
    return df


def save_performance(df):
    out = df.copy()
    out["Views"] = pd.to_numeric(out["Views"], errors="coerce").fillna(0).astype(int)
    _write(out[PERF_COLS], config.PERFORMANCE_DB)


# ─────────────────────────────────────────────
# DEMO SEED — generated relative to *today* so
# every recording shows a live-looking workspace
# ─────────────────────────────────────────────
def seed_demo(force=False):
    files = [config.DRAFTS_DB, config.SCRIPTS_DB, config.INSPO_DB, config.PERFORMANCE_DB]
    if not force and all(os.path.exists(p) for p in files):
        return False

    rng = random.Random(2026)
    today = datetime.date.today()
    creators = list(load_creators.__wrapped__().keys()) or ["Kiara", "Dev", "Ines"]
    formats = load_formats.__wrapped__()
    fmt_names = list(formats.keys())
    interns = [u["display_name"] for u in load_users.__wrapped__() if u["role"] == "INTERN"] or ["Intern 1"]

    # 14 days of shipped history (weekdays heavier)
    hist = []
    for back in range(14, 0, -1):
        day = today - datetime.timedelta(days=back)
        n = rng.randint(4, 9) if day.weekday() < 6 else rng.randint(0, 2)
        for _ in range(n):
            f = rng.choice(fmt_names)
            hist.append({
                "deployed_at": f"{day.isoformat()} {rng.randint(10, 18):02d}:{rng.randint(0, 59):02d}",
                "deploy_date": day.isoformat(), "creator": rng.choice(creators), "format": f,
                "script_type": formats[f]["script_type"], "deployed_by": rng.choice(interns + ["Team Lead"]),
                "result": "SHIPPED",
            })
    _write(pd.DataFrame(hist, columns=SCRIPT_COLS), config.SCRIPTS_DB)

    # A few drafts so the Review Queue and Inbox aren't empty
    def draft(intern, creator, f, status, mins_ago, reviewed=False):
        t = datetime.datetime.now() - datetime.timedelta(minutes=mins_ago)
        it = formats[f]["iterations"][0].replace("{HASHTAGS}", config.BRAND_HASHTAGS).replace("[PASTE LINK]", "https://www.instagram.com/reel/DEMO" + uuid.uuid4().hex[:6].upper() + "/")
        return {
            "id": uuid.uuid4().hex[:8], "created_at": t.strftime("%Y-%m-%d %H:%M"), "intern": intern,
            "creator": creator, "format": f, "script_type": formats[f]["script_type"], "content": it,
            "status": status, "reviewed_at": t.strftime("%Y-%m-%d %H:%M") if reviewed else "",
            "reviewed_by": "Team Lead" if reviewed else "", "deploy_date": today.isoformat(),
        }

    i1 = interns[0]
    i2 = interns[1] if len(interns) > 1 else interns[0]
    seed = [
        draft(i1, creators[0], fmt_names[0], PENDING, 40),
        draft(i1, creators[1], fmt_names[0], PENDING, 40),
        draft(i1, creators[2 % len(creators)], fmt_names[1], PENDING, 25),
        draft(i2, creators[3 % len(creators)], fmt_names[2], PENDING, 18),
        draft(i2, creators[4 % len(creators)], fmt_names[2], PENDING, 18),
        draft(i1, creators[5 % len(creators)], fmt_names[3], APPROVED, 90, reviewed=True),
        draft(i1, creators[0], fmt_names[4 % len(fmt_names)], REJECTED, 120, reviewed=True),
    ]
    _write(pd.DataFrame(seed, columns=DRAFT_COLS), config.DRAFTS_DB)

    inspo = []
    for i, st_ in enumerate(["Approved", "Approved", "Pending", "Pending", "Rejected", "Pending"]):
        d = today - datetime.timedelta(days=i // 2)
        inspo.append({"Date": d.strftime("%d %b"), "Inspiration Link": f"https://www.instagram.com/reel/DEMO{1000 + i}/",
                      "Format": fmt_names[i % len(fmt_names)], "Status": st_, "Added By": interns[i % len(interns)]})
    _write(pd.DataFrame(inspo, columns=INSPO_COLS), config.INSPO_DB)

    perf = []
    for c in creators[:5]:
        f = rng.choice(fmt_names)
        perf.append({"Creator": c, "Top Content": f"{f} — hook v{rng.randint(1, 3)}",
                     "Views": rng.choice([18400, 42700, 96300, 210500, 1240000]),
                     "Platform": rng.choice(["Instagram", "TikTok", "YT Shorts"]), "Format": f,
                     "Milestone URL": f"https://www.instagram.com/reel/DEMO{rng.randint(2000, 2999)}/"})
    _write(pd.DataFrame(perf, columns=PERF_COLS), config.PERFORMANCE_DB)
    return True


def parse_date(iso):
    try:
        return datetime.date.fromisoformat(iso)
    except Exception:
        return datetime.date.today()
