"""Unit tests for employee-name masking used in vendor-facing de-identification."""
from backend.core.masking import mask_name


def test_chinese_three_chars_keeps_first_and_last():
    assert mask_name("王小明") == "王*明"


def test_chinese_two_chars_keeps_first_only():
    assert mask_name("王明") == "王*"


def test_chinese_single_char_unchanged():
    assert mask_name("王") == "王"


def test_western_two_words_keeps_surname():
    assert mask_name("John Smith") == "J* Smith"


def test_western_three_words_keeps_surname_only():
    assert mask_name("Mary Jane Watson") == "M* J* Watson"


def test_empty_string_returns_empty():
    assert mask_name("") == ""


def test_none_returns_empty():
    assert mask_name(None) == ""


def test_surrounding_whitespace_is_trimmed():
    assert mask_name("  John Smith  ") == "J* Smith"
