import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

PROCESSED = Path("data/processed")
INDEX_DIR = Path("index")
MODEL = "BAAI/bge-small-en-v1.5"
MAX_CHARS = 1500


def split_text(text, max_chars=MAX_CHARS):
    pieces, cur = [], ""
    for unit in text.split("\n"):
        while len(unit) > max_chars:
            cut = unit.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if cur:
                pieces.append(cur)
                cur = ""
            pieces.append(unit[:cut])
            unit = unit[cut:].strip()
        if cur and len(cur) + len(unit) + 1 > max_chars:
            pieces.append(cur)
            cur = unit
        else:
            cur = f"{cur}\n{unit}" if cur else unit
    if cur:
        pieces.append(cur)
    return pieces


def build_passages():
    rows = [json.loads(l) for l in open(PROCESSED / "chunks.jsonl", encoding="utf-8")]
    passages = []
    for r in rows:
        for k, piece in enumerate(split_text(r["text"])):
            passages.append({
                "id": f"{r['id']}-p{k}",
                "act": r["act"],
                "section": r["section"],
                "heading": r["heading"],
                "page": r["page"],
                "text": piece,
            })
    return passages


def main():
    INDEX_DIR.mkdir(exist_ok=True)
    passages = build_passages()
    print(f"{len(passages)} passages")

    with open(INDEX_DIR / "passages.jsonl", "w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    model = SentenceTransformer(MODEL)
    texts = [f"{p['act']}, section {p['section']}: {p['heading']}\n{p['text']}" for p in passages]
    emb = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True)

    index = faiss.IndexFlatIP(emb.shape[1])  # inner product = cosine on normalized vectors
    index.add(emb)
    faiss.write_index(index, str(INDEX_DIR / "dense.faiss"))
    print(f"indexed {index.ntotal} vectors, dim {emb.shape[1]}")


if __name__ == "__main__":
    main()