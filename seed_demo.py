"""
SYNAPSE // OS — Google setup checker + demo seeder.

    python seed_demo.py                       # check everything
    python seed_demo.py --sheet <url-or-id>   # save your bifurcation sheet + fill today's tab

What it does:
  1. Confirms credentials.json works and prints the service-account email
  2. Checks the bot can open every creator doc in data/links.csv
  3. Creates today's tab in your bifurcation sheet (copied from data/bifurcation_demo.csv)
"""
import re
import csv
import sys
import datetime

import config

GREEN, RED, AMBER, CYAN, DIM, END = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[90m", "\033[0m"


def ok(msg):   print(f"  {GREEN}✓{END} {msg}")
def bad(msg):  print(f"  {RED}✕{END} {msg}")
def warn(msg): print(f"  {AMBER}!{END} {msg}")


def sheet_id_from(arg):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", arg)
    return m.group(1) if m else arg.strip()


def main():
    print(f"\n{CYAN}SYNAPSE // OS — setup check{END}\n")

    if "--sheet" in sys.argv:
        sid = sheet_id_from(sys.argv[sys.argv.index("--sheet") + 1])
        config.save_config({"bifurcation_sheet_id": sid})
        config.BIFURCATION_SHEET_ID = sid
        ok(f"Saved bifurcation sheet ID to config.json → {sid}")

    # 1. credentials
    print("1. Service account")
    if not config.is_live():
        bad("credentials.json not found in this folder. The app will run in DEMO mode.")
        print(f"     {DIM}See README.md → 'Google setup'{END}\n")
        return
    email = config.service_account_email()
    ok(f"credentials.json loaded")
    print(f"     Share every doc + the sheet with:  {CYAN}{email}{END}  (Editor)\n")

    import google_api

    # 2. creator docs
    print("2. Creator docs (data/links.csv)")
    with open(config.LINKS_FILE, "r", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if len(r) >= 2 and r[0].strip() and r[0].strip().lower() != "creator"]
    ready = 0
    for name, url in ((r[0].strip(), r[1].strip()) for r in rows):
        if "/d/" not in url:
            warn(f"{name:<10} no Google Doc link yet")
            continue
        good, info = google_api.check_doc_access(url)
        if good:
            ready += 1
            ok(f"{name:<10} → \"{info}\"")
        else:
            bad(f"{name:<10} can't open it — share the doc with the email above as Editor  {DIM}({info}){END}")
    print(f"     {ready}/{len(rows)} creators ready to receive deploys\n")

    # 3. bifurcation sheet
    print("3. Bifurcation sheet")
    sid = config.BIFURCATION_SHEET_ID
    if not sid:
        warn("No sheet set. App will use data/bifurcation_demo.csv instead.")
        print(f"     {DIM}Run: python seed_demo.py --sheet <your sheet URL>{END}\n")
        return
    try:
        sheets = google_api._service("sheets", "v4")
        meta = sheets.spreadsheets().get(spreadsheetId=sid).execute()
        tabs = [s["properties"]["title"] for s in meta["sheets"]]
        ok(f"Opened \"{meta['properties']['title']}\" — tabs: {', '.join(tabs)}")
        today = datetime.date.today().isoformat()
        if today in tabs:
            ok(f"Today's tab '{today}' already exists — leaving it alone")
        else:
            sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={
                "requests": [{"addSheet": {"properties": {"title": today, "index": 0}}}]}).execute()
            with open(config.BIFURCATION_DEMO, "r", encoding="utf-8") as f:
                values = list(csv.reader(f))
            sheets.spreadsheets().values().update(
                spreadsheetId=sid, range=f"'{today}'!A1", valueInputOption="RAW", body={"values": values}).execute()
            ok(f"Created tab '{today}' with the demo bifurcation")
    except Exception as e:
        msg = str(e)
        if "not supported" in msg.lower():
            bad("That's an uploaded .xlsx, not a native Google Sheet. File → Save as Google Sheets, use the new link.")
        else:
            bad(f"Can't open the sheet — share it with {email} as Editor  {DIM}({msg[:120]}){END}")
    print(f"\n{CYAN}Done.{END} Run:  streamlit run app.py\n")


if __name__ == "__main__":
    main()
