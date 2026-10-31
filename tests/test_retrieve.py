from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

from retrieve import BM25Retriever, HybridRetriever, RerankRetriever


def p(pid, text=""):
    return {"id": pid, "text": text, "act": "A", "section": pid, "heading": ""}


class Fake:
    def __init__(self, ids):
        self.ids = ids

    def search(self, query, k=5):
        return [p(i) for i in self.ids][:k]


def test_hybrid_fuses_two_rankings_with_rrf():
    hybrid = HybridRetriever(dense=Fake(["a", "b", "c"]), bm25=Fake(["c", "a", "d"]))
    assert [h["id"] for h in hybrid.search("q", k=4)] == ["a", "c", "b", "d"]


def test_hybrid_respects_k_and_does_not_duplicate():
    hybrid = HybridRetriever(dense=Fake(["a", "b"]), bm25=Fake(["a", "b"]))
    ids = [h["id"] for h in hybrid.search("q", k=5)]
    assert ids == ["a", "b"]


def test_rerank_reorders_candidates_by_cross_encoder_score():
    class FakeCE:
        def predict(self, pairs):
            return [0.1, 0.9, 0.5]

    reranker = object.__new__(RerankRetriever)
    reranker.base = Fake(["x", "y", "z"])
    reranker.model = FakeCE()
    reranker.pool = 30
    hits = reranker.search("q", k=3)
    assert [h["id"] for h in hits] == ["y", "z", "x"]
    assert hits[0]["score"] == 0.9


def test_bm25_tokenizer_stems_and_drops_stopwords():
    bm25 = object.__new__(BM25Retriever)
    bm25.stem = PorterStemmer().stem
    tokens = bm25.tokenize("The employees were fired from their jobs")
    assert "the" not in tokens and "were" not in tokens
    assert "fire" in tokens
    assert bm25.tokenize("fired") == bm25.tokenize("firing") or "fire" in bm25.tokenize("fired")


def test_bm25_ranks_the_matching_passage_first():
    passages = [
        p("leave", "annual leave days employee entitled"),
        p("data", "personal data consent data user"),
        p("coercion", "coercion threat agreement voidable"),
    ]
    bm25 = object.__new__(BM25Retriever)
    bm25.stem = PorterStemmer().stem
    bm25.passages = passages
    bm25.bm25 = BM25Okapi([bm25.tokenize(f"{x['heading']} {x['text']}") for x in passages])
    assert bm25.search("how much annual leave", k=3)[0]["id"] == "leave"
