import json
from pathlib import Path

import pymupdf

RAW = Path("data/raw")
OUT = Path("data/processed")


def extract_pdf(path: Path) -> list[dict]:
    doc = pymupdf.open(path)
    return [{"page": i, "text": page.get_text()} for i, page in enumerate(doc, start=1)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(RAW.glob("*.pdf")):
        pages = extract_pdf(pdf)
        out_file = OUT / f"{pdf.stem}.json"
        out_file.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{pdf.name}: {len(pages)} pages -> {out_file}")


if __name__ == "__main__":
    main()