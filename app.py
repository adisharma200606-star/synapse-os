"""
SYNAPSE // OS — content deployment engine for UGC teams.
Run:  streamlit run app.py
"""
import datetime
import html

import streamlit as st

import config
import store
import auth
from deploy import add_log

import ui.write_deploy as page_write_deploy
import ui.review_queue as page_review_queue
import ui.inbox as page_inbox
import ui.inspo_board as page_inspo_board
import ui.daily_log as page_daily_log
import ui.eod as page_eod

# ─────────────────────────────────────────────
# 1. PAGE CONFIG + STYLES
# ─────────────────────────────────────────────
st.set_page_config(page_title="SYNAPSE // OS", page_icon="◆", layout="wide", initial_sidebar_state="expanded")
with open(config.STYLES_FILE, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. SESSION STATE
# ─────────────────────────────────────────────
for k, v in {"logged_in": False, "user_role": "", "username": "", "display_name": "",
             "deploy_log": [], "session_deploys": 0}.items():
    st.session_state.setdefault(k, v)

# Streamlit forgets widget values when you navigate to another page.
# Re-assigning them every run keeps your half-written script alive.
for k in ("wd_format", "wd_date", "wd_type", "wd_inspo", "wd_editor", "wd_creators", "wd_iter", "rq_intern"):
    if k in st.session_state:
        st.session_state[k] = st.session_state[k]

store.seed_demo()  # first run only: builds a live-looking workspace relative to today

LIVE = config.is_live()

# ─────────────────────────────────────────────
# 3. LOGIN
# ─────────────────────────────────────────────
MATRIX_JS = """
<script>
(function(){
  var pd = window.parent.document;
  if (pd.getElementById('syn-matrix')) return;
  var cv = pd.createElement('canvas'); cv.id = 'syn-matrix';
  cv.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:-1;pointer-events:none;background:#08090D;';
  pd.body.style.background = '#08090D';
  pd.body.insertBefore(cv, pd.body.firstChild);
  var ctx = cv.getContext('2d'), W, H, cols, drops, trails, fs = 13, tl = 16;
  var chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
  function init(){ W = cv.width = window.parent.innerWidth; H = cv.height = window.parent.innerHeight;
    cols = Math.floor(W/fs); drops = []; trails = [];
    for (var i=0;i<cols;i++){ drops[i] = Math.random() * -(H/fs); trails[i] = []; } }
  init(); window.parent.addEventListener('resize', init);
  function frame(){
    ctx.clearRect(0,0,W,H); ctx.font = fs + 'px monospace';
    for (var i=0;i<cols;i++){
      var head = Math.floor(drops[i]);
      for (var t=0;t<trails[i].length;t++){
        var age = trails[i].length - t, a = (1 - age/tl) * 0.3;
        if (a <= 0) continue;
        ctx.fillStyle = 'rgba(40,100,255,' + a + ')';
        ctx.fillText(trails[i][t], i*fs, (head-age)*fs);
      }
      if (head >= 0 && head*fs < H){ ctx.fillStyle = 'rgba(80,170,255,0.5)';
        ctx.fillText(chars[Math.floor(Math.random()*chars.length)], i*fs, head*fs); }
      drops[i] += 0.4; trails[i].push(chars[Math.floor(Math.random()*chars.length)]);
      if (trails[i].length > tl) trails[i].shift();
      if (drops[i]*fs > H && Math.random() > 0.975){ drops[i] = Math.random() * -(H/fs/2); trails[i] = []; }
    }
    cv._raf = requestAnimationFrame(frame);
  }
  cv._raf = requestAnimationFrame(frame);
})();
</script>"""

KILL_MATRIX_JS = """
<script>
(function(){ var pd = window.parent.document, cv = pd.getElementById('syn-matrix');
  if (cv){ window.parent.cancelAnimationFrame(cv._raf); cv.remove(); } })();
</script>"""

def run_js(snippet):
    """Inject a script that can reach the main page (matrix rain on login)."""
    if hasattr(st, "iframe"):
        st.iframe(snippet, height=1)
    else:  # older Streamlit
        import streamlit.components.v1 as components
        components.html(snippet, height=0)


if not st.session_state.logged_in:
    st.markdown("<style>section[data-testid='stSidebar']{display:none;}"
                "[data-testid='stAppViewContainer'],[data-testid='stMain'],.stApp{background:transparent!important;}"
                "[data-testid='stMainBlockContainer']{position:relative;z-index:1;}</style>", unsafe_allow_html=True)
    run_js(MATRIX_JS)
    st.markdown('<div class="syn-login-title">SYNAPSE<span>//</span>OS</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="syn-login-sub">{html.escape(config.ORG_NAME)} · Restricted access</div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        with st.form("login"):
            username = st.text_input("Username", placeholder="tl1 / intern1")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("INITIALIZE SESSION", width="stretch")
        if submitted:
            user = auth.authenticate(username, password)
            if user:
                st.session_state.update(logged_in=True, user_role=user["role"], username=user["username"],
                                        display_name=user["display_name"])
                add_log(f"Session initialised — {user['display_name']} [{user['role']}]", "info")
                st.rerun()
            else:
                st.error("Invalid credentials.")
        if not LIVE:
            st.markdown('<div class="syn-login-foot">DEMO · TEAM LEAD tl1 / tl123 · INTERN intern1 / pass1</div>',
                        unsafe_allow_html=True)
    st.stop()

run_js(KILL_MATRIX_JS)

# ─────────────────────────────────────────────
# 4. SIDEBAR
# ─────────────────────────────────────────────
role = st.session_state.user_role
name = st.session_state.display_name
creators = store.load_creators()
pending_total = int((store.drafts()["status"] == store.PENDING).sum())
inbox_ready = int(((store.drafts()["intern"] == name) & (store.drafts()["status"] == store.APPROVED)).sum())

with st.sidebar:
    status_cls, status_txt = ("", "LIVE · GOOGLE CONNECTED") if LIVE else ("demo", "DEMO MODE · DEPLOYS SIMULATED")
    st.markdown(f"""
    <div class="syn-wordmark">
        <div class="syn-wordmark-title">SYNAPSE<span>//</span>OS</div>
        <div class="syn-wordmark-sub">Content deployment engine · {config.VERSION}</div>
        <div class="syn-status-row"><div class="syn-status-dot {status_cls}"></div>
        <div class="syn-status-text {status_cls}">{status_txt}</div></div>
    </div>
    <div class="syn-role-badge"><span class="syn-role-label">{html.escape(name)}</span>
        <span class="syn-role-value">{role}</span></div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="syn-nav-label">Navigation</div>', unsafe_allow_html=True)
    nav = ["WRITE & DEPLOY", "INSPO BOARD", "DAILY LOG", "EOD REPORT"]
    nav.insert(1, "REVIEW QUEUE" if role == auth.TEAM_LEAD else "MY INBOX")
    page = st.radio("Navigation", nav, key="nav", label_visibility="collapsed")
    if role == auth.TEAM_LEAD and pending_total:
        st.caption(f"◆ {pending_total} script{'s' if pending_total != 1 else ''} waiting in your review queue")
    if role == auth.INTERN and inbox_ready:
        st.caption(f"◆ {inbox_ready} approved script{'s' if inbox_ready != 1 else ''} ready to publish")

    st.markdown('<div class="syn-target-label">Creator lookup</div>', unsafe_allow_html=True)
    sel = st.selectbox("Creator", list(creators.keys()) or ["— no creators —"], key="sb_creator", label_visibility="collapsed")
    if sel in creators:
        url = creators[sel]
        has_doc = "/d/" in url
        last = store.scripts()
        last = last[last["creator"] == sel]["deployed_at"].max() if not last.empty else ""
        st.markdown(f"""
        <div class="syn-creator-card"><div class="syn-creator-name">{html.escape(sel)}</div>
        <div class="syn-creator-meta">LAST SCRIPT · {last if isinstance(last, str) and last else "NEVER"}</div></div>
        <a class="syn-open-doc{'' if has_doc else ' off'}" href="{url if has_doc else '#'}" target="_blank">
        {'↗ OPEN GOOGLE DOC' if has_doc else 'NO DOC LINKED YET'}</a>
        """, unsafe_allow_html=True)
        for platform, link in store.load_socials(sel):
            st.markdown(f'<a class="syn-uplink-btn" href="{link}" target="_blank">{platform}</a>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        if st.button("↻ RESYNC", width="stretch", help="Re-pull the bifurcation sheet and reload data"):
            st.cache_data.clear()
            add_log("Caches cleared — data re-synced", "info")
            st.rerun()
    with s2:
        if st.button("LOGOUT", width="stretch"):
            st.session_state.clear()
            st.rerun()

# ─────────────────────────────────────────────
# 5. CONTEXT BAR
# ─────────────────────────────────────────────
st.markdown(f"""
<div class="syn-ctx"><div class="syn-ctx-left">
  <span class="syn-ctx-seg">SYNAPSE<b>//</b>OS</span><span class="syn-ctx-sep">›</span>
  <span class="syn-ctx-seg"><b>{page}</b></span><span class="syn-ctx-sep">›</span>
  <span class="syn-ctx-seg">ROLE: <b>{role}</b></span><span class="syn-ctx-sep">›</span>
  <span class="syn-ctx-seg">SESSION DEPLOYS: <b>{st.session_state.session_deploys}</b></span>
</div><div class="syn-ctx-clock">{datetime.datetime.now().strftime("%a %d %b %Y · %H:%M")}</div></div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 6. ROUTING
# ─────────────────────────────────────────────
if page == "WRITE & DEPLOY":
    page_write_deploy.render(role, name)
elif page == "REVIEW QUEUE":
    page_review_queue.render(name)
elif page == "MY INBOX":
    page_inbox.render(name)
elif page == "INSPO BOARD":
    page_inspo_board.render(name)
elif page == "DAILY LOG":
    page_daily_log.render(name)
elif page == "EOD REPORT":
    page_eod.render(name)
