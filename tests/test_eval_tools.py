import run_eval
from eval_answers import gold_labels
from rescore import mentions, pure_abstain


def test_section_id_strips_the_passage_suffix():
    assert run_eval.section_id({"id": "employment_act-60E-p3"}) == "employment_act-60E"


def test_collapse_keeps_first_passage_per_section_in_order():
    hits = [{"id": "x-1-p0"}, {"id": "x-1-p1"}, {"id": "x-2-p0"}, {"id": "x-1-p2"}, {"id": "x-3-p0"}]
    assert run_eval.collapse(hits) == ["x-1", "x-2", "x-3"]
    assert run_eval.collapse(hits, k=2) == ["x-1", "x-2"]


def test_first_gold_rank():
    assert run_eval.first_gold_rank(["a", "b", "c"], {"c", "z"}) == 3
    assert run_eval.first_gold_rank(["a", "b"], {"z"}) is None


def test_metrics_for():
    rows = [{"rank": 1}, {"rank": 3}, {"rank": None}, {"rank": 6}]
    m = run_eval.metrics_for(rows)
    assert m["n"] == 4
    assert (m["hit@1"], m["hit@3"], m["hit@5"], m["hit@10"]) == (0.25, 0.5, 0.5, 0.75)
    assert m["mrr@10"] == 0.375
    assert run_eval.metrics_for([]) is None


def test_gold_labels_turns_ids_into_citation_labels():
    assert gold_labels(["employment_act-60E", "pdpa-8"]) == {
        "Employment Act 1955 s.60E",
        "Personal Data Protection Act 2010 s.8",
    }


def test_pure_abstain_only_when_answer_starts_with_the_phrase():
    assert pure_abstain("I don't know based on the provided Acts. The excerpts do not say.")
    assert not pure_abstain("Probably yes [Contracts Act 1950 s.19]. I don't know based on the provided Acts.")


def test_mentions_counts_bracket_and_inline_references():
    row = {
        "cited": ["Employment Act 1955 s.60E"],
        "answer": "Under the Contracts Act 1950 s.11 a person must be of sound mind.",
    }
    assert mentions(row) == {"Employment Act 1955 s.60E", "Contracts Act 1950 s.11"}
