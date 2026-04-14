import pytest
from lcl.core.tokens import count_tokens


def test_count_tokens_english():
    result = count_tokens("read the file and check for errors")
    assert result > 0
    assert isinstance(result, int)


def test_count_tokens_cjk():
    result = count_tokens("读文和测错")
    assert result > 0


def test_count_tokens_empty():
    result = count_tokens("")
    assert result == 0


def test_cjk_more_compact_than_english():
    english = "read the file and check for errors"
    lcl = "读文和测错"
    english_tokens = count_tokens(english)
    lcl_tokens = count_tokens(lcl)
    # LCL should use fewer tokens for equivalent meaning
    assert lcl_tokens < english_tokens


def test_count_tokens_with_specific_encoding():
    result = count_tokens("hello world", encoding="cl100k_base")
    assert result == 2
