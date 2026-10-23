# CLAUDE.md

Read README.md before doing anything. It covers what this project is, the architecture, the file map, what's done, and how Adi likes to work.

Short version:
- Synapse OS is a personal proof-of-concept tool (Streamlit + Google Docs/Sheets API), **not a SaaS**.
- Run: `source .venv/bin/activate && streamlit run app.py` (DEMO mode without `credentials.json`). Google setup is in `docs/SETUP.md`.
- Explain your approach and get Adi's yes before writing significant code.
- Never commit `credentials.json` or real creator data.
- Pages go through `store.py` / `google_api.py`, never straight to files or Google.
