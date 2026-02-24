import pytest
from video_to_text.pipeline import normalize_text

def test_normalize_text_basic():
    raw = "Hello  World\nNext Line"
    # normalize_text(raw) replaces [ \t]+ with " ", strips each line, merges hyphenated line ends
    assert normalize_text(raw) == "Hello World\nNext Line"

def test_normalize_text_tabs_and_extra_spaces():
    raw = "Word\t\twith\t   many    spaces"
    assert normalize_text(raw) == "Word with many spaces"

def test_normalize_text_hyphen_merge():
    raw = "This is a long hyphen-\nated word."
    # normalize_text merges hyphenated words: "hyphen-" + "\n" + "ated" -> "hyphenated"
    assert normalize_text(raw) == "This is a long hyphenated word."

def test_normalize_text_multiple_newlines():
    raw = "Line 1\n\n\nLine 2\n\n\n\nLine 3"
    # normalize_text replaces 3+ newlines with 2 newlines (double spacing)
    result = normalize_text(raw)
    assert "\n\n\n" not in result
    assert "Line 1\n\nLine 2" in result
    assert "Line 2\n\nLine 3" in result

def test_normalize_text_korean_unicode():
    raw = "안녕\u1105\u1161" # "안녕라" but with decomposable Hangul if any
    # normalize_text uses NFKC
    import unicodedata
    expected = unicodedata.normalize("NFKC", raw)
    assert normalize_text(raw) == expected
