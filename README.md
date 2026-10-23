# SYNAPSE // OS

Content deployment engine for UGC teams. Interns write scripts from a format library, the Team Lead reviews them in one queue, and approved scripts land at the top of every assigned creator's Google Doc in one click.

**Two modes, detected automatically:**

| Mode | When | What happens |
|---|---|---|
| DEMO | no `credentials.json` in the folder | Everything works; deploys are simulated, bifurcation comes from `data/bifurcation_demo.csv` |
| LIVE | `credentials.json` present | Real writes to Google Docs, real bifurcation from your Google Sheet |

---

## 1. Run it on your Mac (5 min)

Open Terminal in the unzipped `synapse-os` folder:

```bash
python3 --version          # needs 3.10+. If lower: brew install python@3.12
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

It opens at http://localhost:8501. Logins (edit in `data/users.csv`):

| Role | Username | Password |
|---|---|---|
| Team Lead | `tl1` | `tl123` |
| Intern 1 | `intern1` | `pass1` |
| Intern 2 | `intern2` | `pass2` |

Next time, just: `cd synapse-os && source .venv/bin/activate && streamlit run app.py`

---

## 2. Google setup → LIVE mode (15 min)

Use your **personal Gmail**, not a college/work account (those often block key creation).

### a. Create the bot
1. Go to https://console.cloud.google.com → create a project called `synapse-os`
2. **APIs & Services → Library** → enable **Google Docs API** and **Google Sheets API**
3. **IAM & Admin → Service Accounts → Create service account** → name it `synapse-bot` → Done (no roles needed)
4. Click the new account → **Keys → Add key → Create new key → JSON**
5. Rename the downloaded file to `credentials.json` and drop it in the `synapse-os` folder

### b. Create the demo workspace in Google Drive
1. Make a folder called `Synapse Demo`
2. Inside it, create one Google Doc per creator (Kiara, Dev, Ines, Tomas, Mei, Rohan) and one Google Sheet called `Bifurcation`
3. **Share the folder** (not each file) with the bot's email as **Editor** — the email is `client_email` inside `credentials.json`, and `seed_demo.py` prints it too
4. Paste each doc's link into `data/links.csv` in place of `PASTE_GOOGLE_DOC_LINK_HERE`

### c. Check everything + seed today's bifurcation
```bash
python seed_demo.py --sheet "<your Bifurcation sheet URL>"
```
You'll get a ✓ / ✕ for the key, every creator doc, and the sheet. It also creates today's tab in the sheet. Restart the app → the sidebar says **LIVE · GOOGLE CONNECTED**.

Run `python seed_demo.py` again on any later day to add that day's tab.

---

## 3. Recording the Loom

```bash
python reset_demo.py     # fresh review queue, inbox, 14 days of history dated to today
```

A tight 2-minute run of show:
1. **Login as intern1** → Write & Deploy → pick a format → script + today's creators load on their own → paste a reel link → it drops into the script → **Submit for review**
2. **Logout → tl1** → Review Queue → edit one line inline → **Approve + Ship all** → progress bar → open a creator doc and show the dated script at the top
3. Write & Deploy as TL → **Send it** straight to 3 docs
4. Daily Log (history + hours saved) → EOD Report (assigned vs shipped)

Have one creator doc open in another tab before you start so the "it actually landed" moment is instant.

---

## 4. Push to GitHub

```bash
brew install gh && gh auth login        # one-time, pick GitHub.com → HTTPS → browser
git init
git add .
git commit -m "Synapse OS v3"
git branch -M main
git remote add origin https://github.com/adisharma200606-star/synapse-os.git
git push -u origin main
```
`credentials.json` is in `.gitignore` and will never be pushed. Before your first push, run `git status` and make sure it isn't listed.

---

## Project map

```
app.py              login, sidebar, routing
config.py           paths, config.json, date-tab resolver, bifurcation parser
google_api.py       every Google call (+ demo fallbacks)
store.py            CSV data layer + demo seed
deploy.py           batch deploy with progress + audit log
auth.py             users and roles
ui/                 one file per page
data/               creators, users, formats library, demo bifurcation, databases
seed_demo.py        Google setup checker + sheet seeder
reset_demo.py       fresh demo data
config.json         sheet ID, brand hashtags, org name
```

**Editing the format library:** `data/formats.json`. Each format has a script type and one or more "takes" (full scripts). `[PASTE LINK]` gets replaced by the inspiration link, `{HASHTAGS}` by `brand_hashtags` in `config.json`.
