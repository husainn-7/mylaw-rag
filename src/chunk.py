import json
import re
from collections import Counter
from pathlib import Path

PROCESSED = Path("data/processed")
STEM = "employment_act"
ACT_NAME = "Employment Act 1955"
SECTION_RE = re.compile(r"^(\d+[A-Z]?)\.(?:\s|$)")


def norm(line):
    return re.sub(r"\d+", "#", line)


def page_lines(page):
    return [l.strip() for l in page["text"].splitlines() if l.strip()]


def find_boilerplate(pages, edge=4, threshold=0.3):
    counts = Counter()
    for p in pages:
        lines = page_lines(p)
        for l in set(norm(x) for x in lines[:edge] + lines[-edge:]):
            counts[l] += 1
    return {k for k, c in counts.items() if c >= threshold * len(pages)}


def clean_pages(pages, edge=4):
    bp = find_boilerplate(pages, edge)
    result = []
    for p in pages:
        lines = page_lines(p)
        n = len(lines)
        for i, line in enumerate(lines):
            at_edge = i < edge or i >= n - edge
            if at_edge and norm(line) in bp:
                continue
            result.append((p["page"], line))
    return result


def ends_clean(line):
    return line.endswith("etc.") or not line.endswith((".", ";", ":", ",", "\u2014"))


def pop_heading(lines):
    """Section title sits right above the section number (can wrap onto 2 lines)."""
    parts = []
    if lines and len(lines[-1]) < 100 and ends_clean(lines[-1]):
        parts.append(lines.pop())
        if parts[0][:1].islower() and lines and len(lines[-1]) < 100 and ends_clean(lines[-1]):
            parts.insert(0, lines.pop())
    while lines and (lines[-1].startswith("PART ") or lines[-1].isupper()):
        lines.pop()
    return " ".join(parts)


def unwrap(lines):
    text = ""
    for line in lines:
        if not text:
            text = line
        elif re.match(r"^\(\w+\)", line):
            text += "\n" + line
        else:
            text += " " + line
    return text


MAX_GAP = 30  # real Acts skip numbers (e.g. 44A -> 57)


def find_body_start(lines):
    """Section 1 of every Malaysian Act contains 'This Act may be cited as'. TOC doesn't."""
    for i, (_, line) in enumerate(lines):
        if re.match(r"^1\.(?:\s|$)", line):
            nearby = " ".join(l for _, l in lines[i:i + 3])
            if "may be cited" in nearby:
                return i
    raise ValueError("could not find section 1")


def split_sections(lines):
    start = find_body_start(lines)
    before = [l for _, l in lines[max(0, start - 6):start]]
    body = lines[start:]
    done = []
    cur = {"section": None, "page": 0, "heading": "", "lines": before}
    last = 0
    for page, line in body:
        if re.match(r"^(FIRST|SECOND|THIRD)?\s*SCHEDULE\b", line):
            break  # schedules restart numbering, handle later
        m = SECTION_RE.match(line)
        if m:
            num = int(re.match(r"\d+", m.group(1)).group())
            if last <= num <= last + MAX_GAP:
                heading = pop_heading(cur["lines"])
                if cur["section"]:
                    done.append(cur)
                cur = {"section": m.group(1), "page": page, "heading": heading, "lines": [line]}
                last = num
                continue
        cur["lines"].append(line)
    if cur["section"]:
        done.append(cur)
    return done


def main():
    pages = json.load(open(PROCESSED / f"{STEM}.json", encoding="utf-8"))
    sections = split_sections(clean_pages(pages))
    out = PROCESSED / f"{STEM}_chunks.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for s in sections:
            chunk = {
                "id": f"{STEM}-{s['section']}",
                "act": ACT_NAME,
                "section": s["section"],
                "heading": s["heading"],
                "page": s["page"],
                "text": unwrap(s["lines"]),
            }
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"{len(sections)} sections -> {out}")
    for s in sections[:6]:
        print(s["section"], "|", s["heading"])
    print("...")
    for s in sections[-3:]:
        print(s["section"], "|", s["heading"])


if __name__ == "__main__":
    main()