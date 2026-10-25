import json
import re
from collections import Counter
from pathlib import Path

PROCESSED = Path("data/processed")
MAX_GAP = 30  # real Acts skip numbers (e.g. 44A -> 57)
SECTION_RE = re.compile(r"^(\d+[A-Z]?)\.(?:\s|$)")

ACTS = [
    {
        "stem": "employment_act",
        "name": "Employment Act 1955",
        "junk": [],
        "stop": [r"^(FIRST|SECOND|THIRD)?\s*SCHEDULE\b"],
    },
    {
        "stem": "pdpa",
        "name": "Personal Data Protection Act 2010",
        "junk": [],
        "stop": [r"^LAWS OF MALAYSIA$", r"^LIST OF AMENDMENTS"],
    },
    {
        "stem": "contracts_act",
        "name": "Contracts Act 1950",
        "junk": [r"^Unannotated Statutes", r"^ACT 136", r"^Page \d+$", r"^1950$",
                 r"^Part [IVXL]+ ", r"^\(Click"],
        "stop": [r"^Appendix$", r"^LIST OF AMENDMENTS"],
        "inline_heading": True,  # PDF prints the title on the number line
    },
]


def norm(line):
    return re.sub(r"\d+", "#", line)


def page_lines(page):
    return [re.sub(r"\s+", " ", l).strip() for l in page["text"].splitlines() if l.strip()]


def find_boilerplate(pages, edge=4, threshold=0.3):
    counts = Counter()
    for p in pages:
        lines = page_lines(p)
        for l in set(norm(x) for x in lines[:edge] + lines[-edge:]):
            counts[l] += 1
    return {k for k, c in counts.items() if c >= threshold * len(pages)}


def clean_pages(pages, junk_patterns, edge=4):
    bp = find_boilerplate(pages, edge)
    junk = [re.compile(p) for p in junk_patterns]
    result = []
    for p in pages:
        lines = page_lines(p)
        n = len(lines)
        for i, line in enumerate(lines):
            at_edge = i < edge or i >= n - edge
            if at_edge and norm(line) in bp:
                continue
            if any(j.match(line) for j in junk):
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


def find_body_start(lines):
    """Section 1 of every Malaysian Act contains 'may be cited'. The TOC doesn't."""
    for i, (_, line) in enumerate(lines):
        if re.match(r"^1\.(?:\s|$)", line):
            nearby = " ".join(l for _, l in lines[i:i + 3])
            if "may be cited" in nearby:
                return i
    raise ValueError("could not find section 1")


def split_sections(lines, stop_patterns):
    stops = [re.compile(p) for p in stop_patterns]
    start = find_body_start(lines)
    before = [l for _, l in lines[max(0, start - 6):start]]
    done = []
    cur = {"section": None, "page": 0, "heading": "", "lines": before}
    last = 0
    for page, line in lines[start:]:
        if any(s.match(line) for s in stops):
            break
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


def inline_heading(section):
    """Some PDFs print the title on the number line: '3. Communication of proposals'."""
    first = section["lines"][0]
    rest = SECTION_RE.sub("", first, count=1).strip()
    if rest and not rest.startswith("(") and len(rest) < 150:
        section["heading"] = rest
        section["lines"] = section["lines"][1:] or [first]


def chunk_act(act):
    pages = json.load(open(PROCESSED / f"{act['stem']}.json", encoding="utf-8"))
    sections = split_sections(clean_pages(pages, act["junk"]), act["stop"])
    if act.get("inline_heading"):
        for s in sections:
            inline_heading(s)
    return sections


def main():
    out = PROCESSED / "chunks.jsonl"
    total = 0
    with open(out, "w", encoding="utf-8") as f:
        for act in ACTS:
            if not (PROCESSED / f"{act['stem']}.json").exists():
                print(f"skip {act['stem']} (no json)")
                continue
            sections = chunk_act(act)
            for s in sections:
                chunk = {
                    "id": f"{act['stem']}-{s['section']}",
                    "act": act["name"],
                    "section": s["section"],
                    "heading": s["heading"],
                    "page": s["page"],
                    "text": unwrap(s["lines"]),
                }
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            total += len(sections)
            print(f"{act['name']}: {len(sections)} sections")
    print(f"total {total} -> {out}")


if __name__ == "__main__":
    main()