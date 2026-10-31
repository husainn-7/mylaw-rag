import json
import re
import sys
from pathlib import Path

ABSTAIN_START = "i don't know based on the provided acts"
INLINE = re.compile(
    r"(Employment Act 1955|Personal Data Protection Act 2010|Contracts Act 1950),? s(?:ection|\.)\s?([0-9]+[A-Z]*)"
)


def pure_abstain(text):
    return text.strip().lower().startswith(ABSTAIN_START)


def mentions(row):
    """Sections the answer points at: [bracket] citations plus inline 'Act s.X' mentions."""
    found = set(row["cited"])
    found |= {f"{a} s.{n}" for a, n in INLINE.findall(row["answer"])}
    return found


def pct(n, d):
    return f"{n}/{d} = {n / d:.0%}" if d else "n/a"


def main(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    ans = [r for r in rows if r["answerable"]]
    oos = [r for r in rows if not r["answerable"]]

    for r in ans:
        r["pure_abstain"] = pure_abstain(r["answer"])
        r["strict_ok"] = bool(set(r["gold"]) & set(r["cited"])) and not r["pure_abstain"]
        r["lenient_ok"] = bool(set(r["gold"]) & mentions(r)) and not r["pure_abstain"]

    in_ctx = [r for r in ans if r["gold_in_context"]]
    no_ctx = [r for r in ans if not r["gold_in_context"]]

    print(f"=== rescored: {path.name} ===")
    print(f"answerable questions: {len(ans)} ({sum(r['split'] == 'easy' for r in ans)} easy, "
          f"{sum(r['split'] == 'hard' for r in ans)} hard)\n")

    print("END TO END (all answerable)")
    print("  cites a gold section, strict [bracket] format :", pct(sum(r["strict_ok"] for r in ans), len(ans)))
    print("  points at a gold section (bracket or inline) :", pct(sum(r["lenient_ok"] for r in ans), len(ans)))
    for split in ("easy", "hard"):
        sub = [r for r in ans if r["split"] == split]
        print(f"    {split}: lenient {pct(sum(r['lenient_ok'] for r in sub), len(sub))}")

    print("\nWHEN RETRIEVAL FOUND THE SECTION (gold in top 3):", len(in_ctx))
    print("  answered with a gold section (lenient)       :", pct(sum(r["lenient_ok"] for r in in_ctx), len(in_ctx)))
    print("  model abstained anyway (model failure)       :", pct(sum(r["pure_abstain"] for r in in_ctx), len(in_ctx)))

    print("\nWHEN RETRIEVAL MISSED THE SECTION:", len(no_ctx))
    print("  model said 'I don't know' (correct behavior) :", pct(sum(r["pure_abstain"] for r in no_ctx), len(no_ctx)))
    print("  model answered anyway (risky)                :", pct(sum(not r["pure_abstain"] for r in no_ctx), len(no_ctx)))

    print("\nOUT-OF-SCOPE QUESTIONS:", len(oos))
    print("  clean abstention                             :", pct(sum(pure_abstain(r["answer"]) for r in oos), len(oos)))
    for r in oos:
        if not pure_abstain(r["answer"]):
            print(f"  ANSWERED ANYWAY {r['id']}: {r['question']}\n     -> {r['answer'][:200]}")

    print("\nmodel failures to read (retrieval was right, answer was not):")
    for r in in_ctx:
        if not r["lenient_ok"]:
            kind = "abstained" if r["pure_abstain"] else "answered, wrong or missing section"
            print(f"  {r['id']} [{r['split']}] {kind}: {r['question']}")

    print("\nretrieval failures (gold not in top 3, answered anyway):")
    for r in no_ctx:
        if not r["pure_abstain"]:
            print(f"  {r['id']} [{r['split']}]: {r['question']}")


if __name__ == "__main__":
    default = Path("eval/results/answers_full_colab_qwen7b.jsonl")
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else default)