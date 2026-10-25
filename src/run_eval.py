import json
import sys
from pathlib import Path

EVAL = Path("eval/questions.jsonl")
RESULTS = Path("eval/results")
FETCH = 40  # passages to pull before collapsing to sections
TOP_SECTIONS = 10


def section_id(passage):
    return passage["id"].rsplit("-p", 1)[0]


def collapse(hits, k=TOP_SECTIONS):
    """Several passages can come from one section. Keep the first (best) per section."""
    seen, ranked = set(), []
    for h in hits:
        sid = section_id(h)
        if sid not in seen:
            seen.add(sid)
            ranked.append(sid)
        if len(ranked) == k:
            break
    return ranked


def first_gold_rank(ranked, gold):
    for i, sid in enumerate(ranked, start=1):
        if sid in gold:
            return i
    return None


def evaluate(name, search):
    questions = [json.loads(l) for l in open(EVAL, encoding="utf-8")]
    answerable = [q for q in questions if q["answerable"]]
    rows = []
    for q in answerable:
        ranked = collapse(search(q["question"], FETCH))
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "gold": q["gold"],
            "ranked": ranked,
            "rank": first_gold_rank(ranked, set(q["gold"])),
        })

    n = len(rows)

    def hit(k):
        return sum(1 for r in rows if r["rank"] and r["rank"] <= k) / n

    metrics = {
        "method": name,
        "n": n,
        "hit@1": round(hit(1), 3),
        "hit@3": round(hit(3), 3),
        "hit@5": round(hit(5), 3),
        "hit@10": round(hit(10), 3),
        "mrr@10": round(sum(1 / r["rank"] for r in rows if r["rank"]) / n, 3),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{name}.json"
    out.write_text(json.dumps({"metrics": metrics, "rows": rows}, indent=2), encoding="utf-8")

    print(f"\n=== {name} ({n} questions) ===")
    for key in ("hit@1", "hit@3", "hit@5", "hit@10", "mrr@10"):
        print(f"{key:8s} {metrics[key]:.3f}")

    misses = [r for r in rows if not r["rank"] or r["rank"] > 3]
    print(f"\nnot in top 3 ({len(misses)}):")
    for r in misses:
        print(f"  {r['id']} rank={r['rank']} gold={r['gold']}")
        print(f"      Q: {r['question']}")
        print(f"      got: {r['ranked'][:3]}")
    print(f"\nsaved -> {out}")
    return metrics


def get_search(name):
    if name == "dense":
        from retrieve import DenseRetriever
        return DenseRetriever().search
    raise SystemExit(f"unknown method: {name}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "dense"
    evaluate(name, get_search(name))