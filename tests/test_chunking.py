import pytest

from chunk import clean_pages, find_body_start, inline_heading, pop_heading, split_sections, unwrap


def lines(*texts, page=1):
    return [(page, t) for t in texts]


TOC = lines("CONTENTS", "1. Short title", "2. Interpretation", "20. Penalty")

BODY = lines(
    "Short title and application",
    "1. (1) This Act may be cited as the Test Act 2020.",
    "(2) It applies to everyone.",
    "Interpretation",
    "2. In this Act, unless the context otherwise requires--",
    '"employee" means a person',
    "Minister may prohibit employment other than under contract of",
    "service",
    "2A. (1) The Minister may by order prohibit employment.",
    "General power",
    "4. (1) The Minister may exempt.",
    "Penalty",
    "20. Any person who offends shall be guilty.",
    "FIRST SCHEDULE",
    "1. This is not a section",
)
STOP = [r"^(FIRST|SECOND)?\s*SCHEDULE\b"]


def test_find_body_start_skips_table_of_contents():
    all_lines = TOC + BODY
    start = find_body_start(all_lines)
    assert all_lines[start][1].startswith("1. (1) This Act may be cited")


def test_find_body_start_raises_when_missing():
    with pytest.raises(ValueError):
        find_body_start(lines("nothing useful here"))


def test_split_sections_finds_every_section_in_order():
    sections = split_sections(TOC + BODY, STOP)
    assert [s["section"] for s in sections] == ["1", "2", "2A", "4", "20"]


def test_split_sections_headings_including_wrapped_title():
    headings = {s["section"]: s["heading"] for s in split_sections(TOC + BODY, STOP)}
    assert headings["1"] == "Short title and application"
    assert headings["2"] == "Interpretation"
    assert headings["2A"] == "Minister may prohibit employment other than under contract of service"
    assert headings["4"] == "General power"
    assert headings["20"] == "Penalty"


def test_split_sections_allows_gaps_in_numbering():
    # 4 -> 20 is a gap of 16, like the real 44A -> 57
    assert "20" in [s["section"] for s in split_sections(TOC + BODY, STOP)]


def test_split_sections_stops_at_schedule():
    sections = split_sections(TOC + BODY, STOP)
    assert sections[-1]["section"] == "20"
    assert "This is not a section" not in " ".join(sections[-1]["lines"])


def test_heading_is_not_left_inside_previous_section():
    sections = {s["section"]: s for s in split_sections(TOC + BODY, STOP)}
    assert "Interpretation" not in sections["1"]["lines"]
    assert "service" not in sections["2"]["lines"]


def test_pop_heading_drops_part_titles_above_the_heading():
    body = ["some text.", "PART II", "PRELIMINARY", "Annual leave"]
    assert pop_heading(body) == "Annual leave"
    assert body == ["some text."]


def test_pop_heading_ignores_sentences():
    body = ["This line ends like a sentence."]
    assert pop_heading(body) == ""
    assert body == ["This line ends like a sentence."]


def test_unwrap_joins_wrapped_lines_and_keeps_subsections_on_new_lines():
    text = unwrap([
        "60E. (1) An employee shall be",
        "entitled to leave of--",
        "(a) eight days;",
        "(b) twelve days.",
    ])
    assert text == "60E. (1) An employee shall be entitled to leave of--\n(a) eight days;\n(b) twelve days."


def test_clean_pages_removes_repeating_headers_but_keeps_body():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
    pages = [
        {"page": i, "text": f"{i}\nLaws of Malaysia\nACT 265\n{w} wages shall be paid\nsecond {w} line\n"}
        for i, w in enumerate(words, start=1)
    ]
    kept = [line for _, line in clean_pages(pages, [])]
    assert "Laws of Malaysia" not in kept
    assert "ACT 265" not in kept
    assert "alpha wages shall be paid" in kept
    assert len(kept) == 20


def test_clean_pages_applies_junk_patterns_anywhere_on_the_page():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
    pages = []
    for i, w in enumerate(words, start=1):
        text = "\n".join([
            f"a{w}", f"b{w}", f"c{w}", f"d{w}",
            f"Real {w} text",
            f"Page {i}",
            "Click here to see Annotated Statutes",
            f"e{w}", f"f{w}", f"g{w}", f"h{w}", f"i{w}",
        ])
        pages.append({"page": i, "text": text})
    kept = [line for _, line in clean_pages(pages, [r"^Page \d+$", r"^Click here"])]
    assert "Real alpha text" in kept
    assert not any(line.startswith("Page ") for line in kept)
    assert not any(line.startswith("Click here") for line in kept)


def test_inline_heading_moves_title_off_the_number_line():
    section = {"section": "3", "heading": "", "lines": ["3. Communication of proposals", "The communication is complete when..."]}
    inline_heading(section)
    assert section["heading"] == "Communication of proposals"
    assert section["lines"] == ["The communication is complete when..."]


def test_inline_heading_leaves_subsection_openers_alone():
    section = {"section": "1", "heading": "Short title", "lines": ["1. (1) This Act may be cited as the Test Act."]}
    inline_heading(section)
    assert section["heading"] == "Short title"
    assert len(section["lines"]) == 1
