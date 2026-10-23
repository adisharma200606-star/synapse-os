"""
Wipe drafts / deploy history / inspo / tracker and rebuild a fresh demo
workspace dated around today. Run before recording a Loom.

    python reset_demo.py
"""
import store

store.seed_demo(force=True)
print("Demo data reset — fresh review queue, inbox, and 14 days of history.")
