import html
import os
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

st.set_page_config(page_title="MyLaw-RAG | Malaysian law search", page_icon="⚖️", layout="centered")

REPO_URL = "https://github.com/husainn-7/mylaw-rag"

EXAMPLES = [
    "How many days of annual leave do I get after five years?",
    "My landlord threatened to call the police unless I signed. Can I cancel the agreement?",
    "Can my bank send my personal data to its head office overseas?",
    "What is the minimum wage in Malaysia?",
]

ACT_CLASS = {
    "Employment Act 1955": "emp",
    "Personal Data Protection Act 2010": "pdpa",
    "Contracts Act 1950": "con",
}
ACT_SHORT = {
    "Employment Act 1955": "Employment Act",
    "Personal Data Protection Act 2010": "PDPA 2010",
    "Contracts Act 1950": "Contracts Act",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@600;700&display=swap');

:root {
  --bg: #0B0D12; --card: #12151C; --line: #232938; --text: #E7E9EE; --muted: #98A0AF;
  --gold: #E3B04B; --emp: #E3B04B; --pdpa: #4FC3B8; --con: #A99BFF;
}
html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.stApp {
  background:
    radial-gradient(900px 420px at 50% -80px, rgba(227,176,75,0.13), transparent 70%),
    radial-gradient(600px 300px at 90% 10%, rgba(79,195,184,0.05), transparent 70%),
    var(--bg);
}
header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
.block-container { max-width: 860px; padding-top: 3rem; padding-bottom: 4rem; }

.hero { text-align: center; margin-bottom: 1.6rem; }
.eyebrow { letter-spacing: .22em; font-size: .72rem; color: var(--gold); font-weight: 600; text-transform: uppercase; }
.hero h1 { font-family: 'Playfair Display', Georgia, serif; font-weight: 700; font-size: 3.4rem; line-height: 1.05;
  margin: .5rem 0 .6rem; color: var(--text); letter-spacing: -.01em; padding: 0; }
.hero h1 span { color: var(--gold); }
.sub { color: var(--muted); font-size: 1.02rem; max-width: 620px; margin: 0 auto; line-height: 1.6; }
.chips { display: flex; gap: .5rem; justify-content: center; flex-wrap: wrap; margin-top: 1.1rem; }
.chip { border: 1px solid var(--line); background: rgba(18,21,28,.7); color: #C9CED8; font-size: .8rem;
  padding: .32rem .75rem; border-radius: 999px; }
.chip b { color: var(--text); font-weight: 600; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: .45rem; }
.dot.emp { background: var(--emp); } .dot.pdpa { background: var(--pdpa); } .dot.con { background: var(--con); }

.stTextInput input {
  background: var(--card) !important; border: 1px solid var(--line) !important; border-radius: 14px !important;
  padding: 1rem 1.1rem !important; font-size: 1.05rem !important; color: var(--text) !important;
}
.stTextInput input:focus { border-color: var(--gold) !important; box-shadow: 0 0 0 3px rgba(227,176,75,.16) !important; }
.stTextInput > div > div { background: transparent !important; border: none !important; }

.stButton > button {
  width: 100%; text-align: left; justify-content: flex-start; background: rgba(18,21,28,.65);
  border: 1px solid var(--line); color: #C9CED8; border-radius: 12px; padding: .65rem .9rem;
  font-size: .86rem; line-height: 1.35; min-height: 3.2rem; transition: all .15s ease;
}
.stButton > button:hover { border-color: var(--gold); color: var(--text); background: rgba(227,176,75,.07); }
.stButton > button:focus { box-shadow: 0 0 0 3px rgba(227,176,75,.16) !important; border-color: var(--gold); }
.try { color: var(--muted); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; margin: 1.1rem 0 .5rem; }

.note { color: var(--muted); font-size: .84rem; border-left: 2px solid var(--line); padding: .15rem 0 .15rem .8rem; margin: 1.1rem 0; line-height: 1.55; }
.results-head { display: flex; justify-content: space-between; align-items: baseline; margin: 1.7rem 0 .8rem;
  font-family: 'Playfair Display', Georgia, serif; font-size: 1.35rem; color: var(--text); }
.results-head small { font-family: 'Inter', sans-serif; font-size: .78rem; color: var(--muted); }

.card { background: linear-gradient(180deg, rgba(20,24,33,.95), rgba(15,18,25,.95)); border: 1px solid var(--line);
  border-radius: 16px; padding: 1.15rem 1.3rem; margin-bottom: .9rem; position: relative; overflow: hidden; }
.card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, var(--gold)); }
.card.emp { --accent: var(--emp); } .card.pdpa { --accent: var(--pdpa); } .card.con { --accent: var(--con); }
.card-top { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.rank { font-family: 'Playfair Display', Georgia, serif; color: var(--muted); font-size: .95rem; }
.badge { font-size: .7rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; padding: .2rem .55rem;
  border-radius: 6px; color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }
.secnum { font-weight: 600; color: var(--text); font-size: .95rem; }
.card h3 { font-family: 'Playfair Display', Georgia, serif; font-size: 1.3rem; font-weight: 600; margin: .55rem 0 .5rem;
  color: var(--text); padding: 0; line-height: 1.25; }
.statute { color: #BDC3CF; font-size: .93rem; line-height: 1.7; }
details { margin-top: .5rem; }
summary { cursor: pointer; color: var(--accent, var(--gold)); font-size: .84rem; font-weight: 500; list-style: none; padding: .25rem 0; }
summary::-webkit-details-marker { display: none; }
summary::after { content: " +"; }
details[open] summary::after { content: " \\2212"; }
details .statute { margin-top: .45rem; padding-top: .7rem; border-top: 1px solid var(--line); max-height: 340px; overflow-y: auto; }

.answer { background: linear-gradient(180deg, rgba(227,176,75,.10), rgba(227,176,75,.03)); border: 1px solid rgba(227,176,75,.35);
  border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 1.4rem; }
.answer.abstain { background: rgba(18,21,28,.8); border-color: var(--line); }
.answer .label { letter-spacing: .16em; text-transform: uppercase; font-size: .7rem; color: var(--gold); font-weight: 600; margin-bottom: .5rem; }
.answer .body { color: var(--text); font-size: 1.02rem; line-height: 1.7; }
.cite { display: inline-block; font-size: .74rem; font-weight: 600; color: var(--gold); background: rgba(227,176,75,.12);
  border: 1px solid rgba(227,176,75,.3); border-radius: 6px; padding: .02rem .4rem; margin: 0 .1rem; white-space: nowrap; }
.warn { color: #F0A3A3; font-size: .85rem; margin-top: .6rem; }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .8rem; margin: 2.2rem 0 1.2rem; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem; text-align: center; }
.tile .num { font-family: 'Playfair Display', Georgia, serif; font-size: 2rem; color: var(--gold); line-height: 1.1; }
.tile .cap { color: var(--muted); font-size: .8rem; margin-top: .25rem; }
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .8rem; }
.step { border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem; background: rgba(18,21,28,.55); }
.step .n { color: var(--gold); font-weight: 600; font-size: .75rem; letter-spacing: .14em; }
.step .t { color: var(--text); font-weight: 600; margin: .3rem 0 .25rem; }
.step .d { color: var(--muted); font-size: .86rem; line-height: 1.5; }

.footer { margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .8rem;
  text-align: center; line-height: 1.7; }
.footer a { color: var(--gold); text-decoration: none; }
.footer a:hover { text-decoration: underline; }
</style>
"""


def esc(text):
    return html.escape(text).replace("\n", "<br>")


def one_line(markup):
    """Streamlit's markdown treats blank lines inside HTML as the end of the block, so keep it on one line."""
    return " ".join(line.strip() for line in markup.splitlines() if line.strip())


@st.cache_resource(show_spinner="Loading the search models (the first start takes a minute)...")
def load_pipeline():
    if not Path("index/dense.faiss").exists():
        from index import main as build_index

        build_index()
    from generate import RagPipeline

    return RagPipeline()


def llm_configured():
    return bool(os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("USE_OLLAMA"))


def hero():
    return one_line("""
    <div class="hero">
      <div class="eyebrow">Malaysian law &middot; plain-English search</div>
      <h1>MyLaw<span>-</span>RAG</h1>
      <div class="sub">Ask a question in everyday language and get the exact section of the Act that answers it,
      with the statute text beside it.</div>
      <div class="chips">
        <span class="chip"><span class="dot emp"></span><b>Employment Act 1955</b> &middot; 141 sections</span>
        <span class="chip"><span class="dot pdpa"></span><b>PDPA 2010</b> &middot; 146 sections</span>
        <span class="chip"><span class="dot con"></span><b>Contracts Act 1950</b> &middot; 191 sections</span>
      </div>
    </div>
    """)


def landing():
    return one_line("""
    <div class="tiles">
      <div class="tile"><div class="num">478</div><div class="cap">sections indexed</div></div>
      <div class="tile"><div class="num">85</div><div class="cap">evaluation questions</div></div>
      <div class="tile"><div class="num">6</div><div class="cap">retrieval methods compared</div></div>
    </div>
    <div class="steps">
      <div class="step"><div class="n">01</div><div class="t">Search by meaning</div>
        <div class="d">Your question is matched to sections by what it means, not just the words it shares.</div></div>
      <div class="step"><div class="n">02</div><div class="t">Re-rank the candidates</div>
        <div class="d">A second model reads question and section together and picks the best three.</div></div>
      <div class="step"><div class="n">03</div><div class="t">Cite the section</div>
        <div class="d">Every result links back to the exact section number and its full text.</div></div>
    </div>
    """)


def section_card(rank, label, section):
    act, number = label.rsplit(" s.", 1)
    cls = ACT_CLASS.get(act, "emp")
    text = "\n".join(section["passages"])[:3000]
    preview = text if len(text) <= 420 else text[:420].rsplit(" ", 1)[0] + "..."
    body = f'<div class="statute">{esc(preview)}</div>'
    if len(text) > 420:
        body += f'<details><summary>Read full section</summary><div class="statute">{esc(text)}</div></details>'
    return one_line(
        f'<div class="card {cls}"><div class="card-top"><span class="rank">{rank:02d}</span>'
        f'<span class="badge">{esc(ACT_SHORT.get(act, act))}</span><span class="secnum">Section {esc(number)}</span></div>'
        f'<h3>{esc(section["heading"] or "Section " + number)}</h3>{body}</div>'
    )


def cite_chips(text):
    safe = html.escape(text)
    safe = re.sub(r"\[([^\[\]]*? s\.[0-9]+[A-Z]*[^\[\]]*)\]", r'<span class="cite">\1</span>', safe)
    return safe.replace("\n", "<br>")


def answer_card(res):
    if res["abstained"]:
        inner = f'<div class="label">No answer in the Acts</div><div class="body">{cite_chips(res["answer"])}</div>'
        cls = "answer abstain"
    else:
        inner = f'<div class="label">Answer</div><div class="body">{cite_chips(res["answer"])}</div>'
        cls = "answer"
    if res["invalid_cites"]:
        inner += f'<div class="warn">Heads up: this answer cites sections that were not in the retrieved text: {esc(", ".join(res["invalid_cites"]))}</div>'
    return one_line(f'<div class="{cls}">{inner}</div>')


st.markdown(CSS, unsafe_allow_html=True)
st.markdown(hero(), unsafe_allow_html=True)

if "q" not in st.session_state:
    st.session_state.q = ""


def set_question(text):
    st.session_state.q = text


question = st.text_input(
    "Your question",
    key="q",
    placeholder="Ask anything, e.g. Can my boss fire me without notice?",
    label_visibility="collapsed",
)

if not question.strip():
    st.markdown('<div class="try">Try one of these</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLES):
        cols[i % 2].button(example, key=f"ex{i}", use_container_width=True, on_click=set_question, args=(example,))
    st.markdown(landing(), unsafe_allow_html=True)
else:
    pipe = load_pipeline()
    if llm_configured():
        with st.spinner("Searching the Acts and writing an answer..."):
            try:
                res = pipe.answer(question)
            except Exception as e:
                st.error(f"The language model call failed: {e}")
                st.stop()
        st.markdown(answer_card(res), unsafe_allow_html=True)
        context = res["context"]
    else:
        st.markdown(
            '<div class="note">Showing the most relevant sections. Written answers need a language model, which this free demo does not run; '
            'they were evaluated offline (see the README).</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Searching the Acts..."):
            context = pipe.retrieve(question)

    if context:
        st.markdown(
            f'<div class="results-head"><span>Most relevant sections</span><small>{len(context)} found</small></div>',
            unsafe_allow_html=True,
        )
        for rank, (label, section) in enumerate(context.items(), start=1):
            st.markdown(section_card(rank, label, section), unsafe_allow_html=True)

st.markdown(
    one_line(f"""
    <div class="footer">
      Based on reprints of the Employment Act 1955, the Personal Data Protection Act 2010 and the Contracts Act 1950.<br>
      This is a search tool, not legal advice. &nbsp;&middot;&nbsp;
      <a href="{REPO_URL}" target="_blank">Source code and evaluation</a>
    </div>
    """),
    unsafe_allow_html=True,
)