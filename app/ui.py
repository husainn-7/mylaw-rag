import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

st.set_page_config(page_title="MyLaw-RAG", layout="centered")

EXAMPLES = [
    "How many days of annual leave do I get after five years?",
    "My landlord threatened to call the police unless I signed. Can I cancel the agreement?",
    "Can my bank send my personal data to its head office overseas?",
    "What is the minimum wage in Malaysia?",
]


@st.cache_resource(show_spinner="Loading models (the first start takes a minute)...")
def load_pipeline():
    if not Path("index/dense.faiss").exists():
        from index import main as build_index

        build_index()
    from generate import RagPipeline

    return RagPipeline()


def llm_configured():
    return bool(os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("USE_OLLAMA"))


st.title("MyLaw-RAG")
st.caption(
    "Ask about the Employment Act 1955, the Personal Data Protection Act 2010 and the Contracts Act 1950. "
    "Answers cite the section they come from. Based on reprints of the Acts, not legal advice."
)

if "q" not in st.session_state:
    st.session_state.q = ""

cols = st.columns(2)
for i, example in enumerate(EXAMPLES):
    if cols[i % 2].button(example, key=f"ex{i}", use_container_width=True):
        st.session_state.q = example

question = st.text_input("Your question", key="q", placeholder="e.g. How many days of annual leave do I get?")

if question.strip():
    pipe = load_pipeline()
    if llm_configured():
        with st.spinner("Searching the Acts and writing an answer..."):
            try:
                res = pipe.answer(question)
            except Exception as e:
                st.error(f"The language model call failed: {e}")
                st.stop()
        if res["abstained"]:
            st.warning(res["answer"])
        else:
            st.markdown(res["answer"])
        if res["invalid_cites"]:
            st.error("This answer cites sections that were not in the retrieved text: " + ", ".join(res["invalid_cites"]))
        context = res["context"]
    else:
        st.info("No language model is configured, so this shows the most relevant sections only.")
        with st.spinner("Searching the Acts..."):
            context = pipe.retrieve(question)

    st.subheader("Sources")
    for label, section in context.items():
        with st.expander(f"{label}: {section['heading']}"):
            st.text("\n".join(section["passages"])[:3000])