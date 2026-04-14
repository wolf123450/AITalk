import pytest
from pathlib import Path
from lcl.core.lexicon import load_lexicon
from lcl.core.validator import validate


@pytest.fixture
def lexicon(data_dir: Path):
    return load_lexicon(data_dir / "phase0-lexicon.json")


def test_validate_all_known_symbols(lexicon):
    # 事読文 = "task read file"
    result = validate("事读文", lexicon)
    assert result.is_valid is True
    assert result.total_symbols == 3
    assert result.known_symbols == 3
    assert result.unknown_symbols == []


def test_validate_with_unknown_symbols(lexicon):
    # 事猫文 — 猫 (cat) is not in the lexicon
    result = validate("事猫文", lexicon)
    assert result.is_valid is False
    assert result.unknown_symbols == ["猫"]
    assert result.known_symbols == 2


def test_validate_with_structural_markers(lexicon):
    # 文▲多 = "file MOD many" = "many files"
    result = validate("文▲多", lexicon)
    assert result.is_valid is True
    assert result.marker_count == 1
    assert result.known_symbols == 2  # markers counted separately


def test_validate_with_english_fallback(lexicon):
    # 读◇README.md◈ = "read [ENG: README.md]"
    result = validate("读◇README.md◈", lexicon)
    assert result.is_valid is True
    assert result.english_fallback_count == 1
    assert result.known_symbols == 1


def test_validate_empty_string(lexicon):
    result = validate("", lexicon)
    assert result.is_valid is True
    assert result.total_symbols == 0


def test_validate_only_english_fallback(lexicon):
    result = validate("◇hello world◈", lexicon)
    assert result.is_valid is True
    assert result.english_fallback_count == 1
    assert result.known_symbols == 0


def test_validate_unmatched_eng_start_warns(lexicon):
    result = validate("读◇README.md", lexicon)
    assert "unmatched ENG_START" in result.warnings[0].lower() or len(result.warnings) > 0


def test_validate_neg_marker(lexicon):
    # △成 = "NOT complete"
    result = validate("△成", lexicon)
    assert result.is_valid is True
    assert result.marker_count == 1
    assert result.known_symbols == 1


def test_validate_whitespace_ignored(lexicon):
    result = validate("事 读 文", lexicon)
    assert result.is_valid is True
    assert result.known_symbols == 3
