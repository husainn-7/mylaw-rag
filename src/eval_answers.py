import json
import random
import sys
import time
from pathlib import Path

from generate import RagPipeline

EVAL = Path("eval/questions.jsonl")
RESULTS = Path("eval/results")
N_EASY, N_HARD = 8, 12  # sample sizes; run with "full" to use every question

ACTS = {
    "employment_act": "Employment Act 1955",
    "pdpa": "Personal Data Protection Act 2010",
    "contracts_act": "Contracts Act 1950",
}


def gold_labels(gold):
    out = set()
    for g in gold:
        stem, section = g.rsplit("-", 1)
        out.add(f"{ACTS[stem]} s.{section}")
    return out


def pick_questions(full):
    qs = [json.loads(l) for l in open(EVAL, encoding="utf-8")]
    if full:
        return qs
    rng = random.Random(0)  # fixed seed = same sample every run
    easy = [q for q in qs if q["answerable"] and q.get("split", "easy") == "easy"]
    hard = [q for q in qs if q["answerable"] and q.get("split") == "hard"]
    oos = [q for q in qs if not q["answerable"]]
    return rng.sample(easy, N_EASY) + rng.sample(hard, N_HARD) + oos


def summarize(rows):
    ans = [r for r in rows if r["answerable"]]
    oos = [r for r in rows if not r["answerable"]]

    def pct(n, d):
        return f"{n}/{d} = {n / d:.0%}" if d else "n/a"

    answered = [r for r in ans if not r["abstained"]]
    print(f"\n=== answer eval ({len(ans)} answerable, {len(oos)} out-of-scope) ===")
    print("context recall (gold section in retrieved top 3): ",
          pct(sum(r["gold_in_context"] for r in ans), len(ans)))
    print("false abstentions (said 'don't know' but answerable):",
          pct(sum(r["abstained"] for r in ans), len(ans)))
    print("citation correct (cites a gold section):          ",
          pct(sum(r["citation_correct"] for r in ans), len(ans)))
    print("hallucinated citations (cites unretrieved section):",
          pct(sum(bool(r["invalid_cites"]) for r in answered), len(answered)))
    print("correct abstention on out-of-scope:               ",
          pct(sum(r["abstained"] for r in oos), len(oos)))
    for split in ("easy", "hard"):
        sub = [r for r in ans if r["split"] == split]
        if sub:
            print(f"  {split}: citation correct {pct(sum(r['citation_correct'] for r in sub), len(sub))}")

    bad = [r for r in rows if (r["answerable"] and not r["citation_correct"])
           or (not r["answerable"] and not r["abstained"])]
    print(f"\nproblems to read ({len(bad)}):")
    for r in bad:
        print(f"\n- {r['id']} [{r['split']}] {r['question']}")
        print(f"  gold: {r['gold']}  retrieved: {r['sources']}")
        print(f"  answer: {r['answer'][:300]}")


def main():
    full = len(sys.argv) > 1 and sys.argv[1] == "full"
    out = RESULTS / ("answers_full.jsonl" if full else "answers_sample.jsonl")
    RESULTS.mkdir(parents=True, exist_ok=True)

    questions = pick_questions(full)
    done = {}
    if out.exists():
        for line in open(out, encoding="utf-8"):
            r = json.loads(line)
            done[r["id"]] = r

    todo = [q for q in questions if q["id"] not in done]
    print(f"{len(questions)} questions, {len(done)} already done, {len(todo)} to run")
    if todo:
        pipe = RagPipeline()
        start = time.time()
        with open(out, "a", encoding="utf-8") as f:
            for i, q in enumerate(todo, 1):
                t = time.time()
                res = pipe.answer(q["question"])
                gold = gold_labels(q["gold"])
                row = {
                    "id": q["id"],
                    "split": q.get("split", "easy"),
                    "answerable": q["answerable"],
                    "question": q["question"],
                    "gold": sorted(gold),
                    "answer": res["answer"],
                    "sources": res["sources"],
                    "cited": res["cited"],
                    "invalid_cites": res["invalid_cites"],
                    "abstained": res["abstained"],
                    "gold_in_context": bool(gold & set(res["sources"])),
                    "citation_correct": bool(gold & set(res["cited"])) and not res["abstained"],
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                done[q["id"]] = row
                avg = (time.time() - start) / i
                print(f"[{i}/{len(todo)}] {q['id']} {time.time() - t:.0f}s "
                      f"(~{avg * (len(todo) - i) / 60:.0f} min left)", flush=True)

    summarize([done[q["id"]] for q in questions])


if __name__ == "__main__":
    main()