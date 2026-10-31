import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path):
    return [json.loads(line) for line in open(ROOT / path, encoding="utf-8")]


CHUNKS = read_jsonl("data/processed/chunks.jsonl")
QUESTIONS = read_jsonl("eval/questions.jsonl")


def test_section_counts_per_act():
    counts = Counter(c["act"] for c in CHUNKS)
    assert counts == {
        "Employment Act 1955": 141,
        "Personal Data Protection Act 2010": 146,
        "Contracts Act 1950": 191,
    }


def test_chunk_ids_are_unique_and_text_is_not_empty():
    ids = [c["id"] for c in CHUNKS]
    assert len(ids) == len(set(ids))
    assert all(c["text"].strip() for c in CHUNKS)


def test_every_gold_section_exists_in_the_corpus():
    ids = {c["id"] for c in CHUNKS}
    for q in QUESTIONS:
        for gold in q["gold"]:
            assert gold in ids, f"{q['id']} points at missing section {gold}"


def test_question_ids_are_unique():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))


def test_out_of_scope_questions_have_no_gold_and_answerable_ones_do():
    for q in QUESTIONS:
        assert bool(q["gold"]) == q["answerable"], q["id"]


def test_splits_are_valid():
    assert {q.get("split", "easy") for q in QUESTIONS} <= {"easy", "hard"}
