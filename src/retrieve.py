import json
import re
import sys
from pathlib import Path

import numpy as np

INDEX_DIR = Path("index")
MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

STOPWORDS = set(
    "a an the and or of to in on at by for with from as is are was were be been being it its this that "
    "these those i me my we our you your he she they them his her their do does did can could should would "
    "will shall may might must not no if any what when where who which how about into than then so such".split()
)


def load_passages():
    return [json.loads(l) for l in open(INDEX_DIR / "passages.jsonl", encoding="utf-8")]


class DenseRetriever:
    def __init__(self):
        import faiss
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(MODEL)
        self.index = faiss.read_index(str(INDEX_DIR / "dense.faiss"))
        self.passages = load_passages()

    def search(self, query, k=5):
        q = self.model.encode([QUERY_PREFIX + query], normalize_embeddings=True)
        scores, ids = self.index.search(q, k)
        return [{**self.passages[i], "score": float(s)} for s, i in zip(scores[0], ids[0])]


class BM25Retriever:
    def __init__(self):
        from nltk.stem import PorterStemmer
        from rank_bm25 import BM25Okapi

        self.stem = PorterStemmer().stem
        self.passages = load_passages()
        corpus = [self.tokenize(f"{p['heading']} {p['text']}") for p in self.passages]
        self.bm25 = BM25Okapi(corpus)

    def tokenize(self, text):
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [self.stem(w) for w in words if w not in STOPWORDS]

    def search(self, query, k=5):
        scores = self.bm25.get_scores(self.tokenize(query))
        top = np.argsort(scores)[::-1][:k]
        return [{**self.passages[i], "score": float(scores[i])} for i in top]


class HybridRetriever:
    """Reciprocal rank fusion: score = sum of 1 / (60 + rank) over each ranking."""

    def __init__(self, dense=None, bm25=None):
        self.dense = dense or DenseRetriever()
        self.bm25 = bm25 or BM25Retriever()

    def search(self, query, k=5, pool=50, rrf_k=60):
        fused = {}
        for hits in (self.dense.search(query, pool), self.bm25.search(query, pool)):
            for rank, h in enumerate(hits, start=1):
                entry = fused.setdefault(h["id"], {**h, "rrf": 0.0})
                entry["rrf"] += 1.0 / (rrf_k + rank)
        ranked = sorted(fused.values(), key=lambda x: -x["rrf"])[:k]
        return [{**h, "score": h["rrf"]} for h in ranked]


class RerankRetriever:
    """Take candidates from a base retriever, then re-score each (query, passage) pair
    with a cross-encoder that reads both together."""

    def __init__(self, model_name, base=None, pool=30):
        from sentence_transformers import CrossEncoder

        self.base = base or DenseRetriever()
        self.model = CrossEncoder(model_name, max_length=512)
        self.pool = pool

    def search(self, query, k=5):
        cands = self.base.search(query, self.pool)
        pairs = [(query, f"{c['act']}, section {c['section']}: {c['heading']}\n{c['text']}") for c in cands]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(scores, cands), key=lambda x: -x[0])[:k]
        return [{**c, "score": float(s)} for s, c in ranked]


MINILM = "cross-encoder/ms-marco-MiniLM-L-12-v2"
BGE = "BAAI/bge-reranker-base"

METHODS = {
    "dense": DenseRetriever,
    "bm25": BM25Retriever,
    "hybrid": HybridRetriever,
    "dense_rerank_minilm": lambda: RerankRetriever(MINILM),
    "dense_rerank_bge": lambda: RerankRetriever(BGE),
    "hybrid_rerank_bge": lambda: RerankRetriever(BGE, base=HybridRetriever()),
}


if __name__ == "__main__":
    args = sys.argv[1:]
    method = args.pop(0) if args and args[0] in METHODS else "dense"
    query = " ".join(args) or "How many days of annual leave do I get?"
    for hit in METHODS[method]().search(query):
        print(f"{hit['score']:.3f} | {hit['act']} s.{hit['section']} {hit['heading']}")
        print("    ", hit["text"][:150].replace("\n", " "))