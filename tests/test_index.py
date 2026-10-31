from index import MAX_CHARS, build_passages, split_text


def squash(text):
    return "".join(text.split())


def test_short_text_stays_in_one_piece():
    assert split_text("A short section.") == ["A short section."]


def test_long_text_is_split_under_the_limit_without_losing_words():
    text = "\n".join(f"({i}) " + "word " * 60 for i in range(1, 30))
    pieces = split_text(text)
    assert len(pieces) > 1
    assert all(len(p) <= MAX_CHARS for p in pieces)
    assert squash("".join(pieces)) == squash(text)


def test_one_enormous_line_is_split_at_spaces():
    text = "lorem " * 1000
    pieces = split_text(text)
    assert all(len(p) <= MAX_CHARS for p in pieces)
    assert squash("".join(pieces)) == squash(text)


def test_every_real_section_becomes_at_least_one_passage():
    passages = build_passages()
    assert len(passages) >= 478
    assert all(len(p["text"]) <= MAX_CHARS for p in passages)
    assert len({p["id"] for p in passages}) == len(passages)
