import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from retrieve import MINILM, RerankRetriever

TOP_SECTIONS = 3
MAX_CHARS_PER_SECTION = 1200
ABSTAIN = "I don't know based on the provided Acts."

SYSTEM = f"""You answer questions about Malaysian law using ONLY the excerpts provided from the \
Employment Act 1955, the Personal Data Protection Act 2010 and the Contracts Act 1950.

Rules:
- Use only the excerpts. If they do not contain the answer, reply exactly: {ABSTAIN}
- Cite every claim with the section label exactly as shown, like [Employment Act 1955 s.60E]. \
Only cite sections that appear in the excerpts.
- Be concise: at most 6 sentences, plain language.
- Do not add legal advice beyond what the text says."""


def _post(url, payload, headers, timeout=300):
    """POST JSON. Retries when the provider says 'rate limited' (HTTP 429)."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, body, {"Content-Type": "application/json", "User-Agent": "mylaw-rag/0.1", **headers}
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                wait = float(e.headers.get("retry-after", 20)) + 1
                print(f"  rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            raise


def llm(system, user):
    """Claude API if ANTHROPIC_API_KEY is set, else Groq if GROQ_API_KEY is set, else local Ollama."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"),
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    if os.environ.get("GROQ_API_KEY"):
        data = _post(
            "https://api.groq.com/openai/v1/chat/completions",
            {
                "model": os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
                "temperature": 0,
                "max_tokens": 400,
                "messages": messages,
            },
            {"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        )
        return data["choices"][0]["message"]["content"].strip()

    data = _post(
        "http://localhost:11434/api/chat",
        {
            "model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096},
            "messages": messages,
        },
        {},
    )
    return data["message"]["content"].strip()


SECTION_REF = re.compile(r"([A-Za-z][A-Za-z0-9 ]*? s\.[0-9]+[A-Z]*)(?:\([A-Za-z0-9]+\))*")


def parse_citations(text):
    """Find [Act s.X] citations. Tolerates subsections like s.60E(1)(c) and lists in one bracket."""
    cited = []
    for bracket in re.findall(r"\[([^\[\]]+)\]", text):
        for part in re.split(r"[;,](?=\s*[A-Z])", bracket):
            m = SECTION_REF.fullmatch(part.strip())
            if m:
                cited.append(m.group(1))
    return cited


def label(p):
    return f"{p['act']} s.{p['section']}"


class RagPipeline:
    def __init__(self, retriever=None):
        self.retriever = retriever or RerankRetriever(MINILM)

    def retrieve(self, question):
        """Top sections (best first), each with its retrieved passages in order."""
        sections = {}
        for hit in self.retriever.search(question, 15):
            sections.setdefault(label(hit), {"heading": hit["heading"], "passages": []})["passages"].append(hit["text"])
        return dict(list(sections.items())[:TOP_SECTIONS])

    def answer(self, question):
        sources = self.retrieve(question)
        context = "\n\n".join(
            f"[{lab}] {s['heading']}\n{chr(10).join(s['passages'])[:MAX_CHARS_PER_SECTION]}"
            for lab, s in sources.items()
        )
        text = llm(SYSTEM, f"Excerpts:\n\n{context}\n\nQuestion: {question}")
        cited = parse_citations(text)
        return {
            "question": question,
            "answer": text,
            "sources": list(sources),
            "cited": cited,
            "invalid_cites": [c for c in cited if c not in sources],
            "abstained": ABSTAIN.lower() in text.lower(),
        }


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How many days of annual leave do I get?"
    r = RagPipeline().answer(q)
    print("\n" + r["answer"])
    print("\nretrieved:", ", ".join(r["sources"]))
    if r["invalid_cites"]:
        print("WARNING, cited sections not in retrieved context:", r["invalid_cites"])