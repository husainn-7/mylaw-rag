import generate
from generate import ABSTAIN, RagPipeline, label, parse_citations


def test_parse_citations_plain():
    assert parse_citations("Sixteen days [Employment Act 1955 s.60E].") == ["Employment Act 1955 s.60E"]


def test_parse_citations_accepts_subsections():
    assert parse_citations("See [Employment Act 1955 s.60E(1)(c)].") == ["Employment Act 1955 s.60E"]


def test_parse_citations_accepts_lists_in_one_bracket():
    text = "Both apply [Employment Act 1955 s.60E, Employment Act 1955 s.60D]."
    assert parse_citations(text) == ["Employment Act 1955 s.60E", "Employment Act 1955 s.60D"]


def test_parse_citations_letter_suffix_sections():
    assert parse_citations("[Contracts Act 1950 s.2A]") == ["Contracts Act 1950 s.2A"]


def test_parse_citations_ignores_unrelated_brackets():
    assert parse_citations("No citations. [1] and [see above]") == []


def test_label():
    assert label({"act": "Contracts Act 1950", "section": "19"}) == "Contracts Act 1950 s.19"


class FakeRetriever:
    def search(self, question, k):
        return [
            {"act": "Employment Act 1955", "section": "60E", "heading": "Annual leave", "text": "60E. (1) sixteen days"},
            {"act": "Employment Act 1955", "section": "60E", "heading": "Annual leave", "text": "(2) more text"},
            {"act": "Contracts Act 1950", "section": "15", "heading": "Coercion", "text": "Coercion is a threat"},
            {"act": "Contracts Act 1950", "section": "19", "heading": "Voidability", "text": "voidable"},
            {"act": "Contracts Act 1950", "section": "20", "heading": "Mistake", "text": "never shown"},
        ]


def test_retrieve_groups_passages_by_section_and_keeps_top_sections():
    sources = RagPipeline(retriever=FakeRetriever()).retrieve("q")
    assert list(sources) == ["Employment Act 1955 s.60E", "Contracts Act 1950 s.15", "Contracts Act 1950 s.19"]
    assert len(sources["Employment Act 1955 s.60E"]["passages"]) == 2


def test_answer_flags_citations_that_were_not_retrieved(monkeypatch):
    monkeypatch.setattr(generate, "llm", lambda system, user: "Yes [Employment Act 1955 s.60E]. Also [Contracts Act 1950 s.99].")
    result = RagPipeline(retriever=FakeRetriever()).answer("How many days of leave?")
    assert result["cited"] == ["Employment Act 1955 s.60E", "Contracts Act 1950 s.99"]
    assert result["invalid_cites"] == ["Contracts Act 1950 s.99"]
    assert result["abstained"] is False
    assert "Employment Act 1955 s.60E" in result["context"]


def test_answer_detects_abstention(monkeypatch):
    monkeypatch.setattr(generate, "llm", lambda system, user: ABSTAIN)
    result = RagPipeline(retriever=FakeRetriever()).answer("What is the minimum wage?")
    assert result["abstained"] is True
    assert result["cited"] == []


def test_prompt_contains_question_labels_and_is_truncated(monkeypatch):
    seen = {}

    def fake_llm(system, user):
        seen["system"], seen["user"] = system, user
        return "ok"

    class Long(FakeRetriever):
        def search(self, question, k):
            return [{"act": "Employment Act 1955", "section": "1", "heading": "H", "text": "x" * 5000}]

    monkeypatch.setattr(generate, "llm", fake_llm)
    RagPipeline(retriever=Long()).answer("my question")
    assert "[Employment Act 1955 s.1] H" in seen["user"]
    assert "Question: my question" in seen["user"]
    assert "x" * (generate.MAX_CHARS_PER_SECTION + 1) not in seen["user"]
    assert ABSTAIN in seen["system"]
