import json
import sys
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("index")
MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class DenseRetriever:
    def __init__(self):
        self.model = SentenceTransformer(MODEL)
        self.index = faiss.read_index(str(INDEX_DIR / "dense.faiss"))
        self.passages = [
            json.loads(l) for l in open(INDEX_DIR / "passages.jsonl", encoding="utf-8")
        ]

    def search(self, query, k=5):
        q = self.model.encode([QUERY_PREFIX + query], normalize_embeddings=True)
        scores, ids = self.index.search(q, k)
        return [{**self.passages[i], "score": float(s)} for s, i in zip(scores[0], ids[0])]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "How many days of annual leave do I get?"
    retriever = DenseRetriever()
    for hit in retriever.search(query):
        print(f"{hit['score']:.3f} | {hit['act']} s.{hit['section']} {hit['heading']}")
        print("    ", hit["text"][:150].replace("\n", " "))