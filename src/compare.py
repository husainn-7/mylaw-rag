import json
from pathlib import Path

ORDER = ["dense", "bm25", "hybrid", "dense_rerank_minilm", "dense_rerank_bge", "hybrid_rerank_bge"]
files = {p.stem: p for p in Path("eval/results").glob("*.json")}
names = [n for n in ORDER if n in files] + sorted(n for n in files if n not in ORDER)

COLS = ["hit@1", "hit@3", "hit@5", "hit@10", "mrr@10"]
for split in ("hard", "easy", "all"):
    print(f"\n{split.upper()}")
    print(f"{'method':14s}" + "".join(f"{c:>8s}" for c in COLS))
    for n in names:
        m = json.loads(files[n].read_text(encoding="utf-8"))["metrics"].get(split)
        if m:
            print(f"{n:14s}" + "".join(f"{m[c]:8.3f}" for c in COLS))