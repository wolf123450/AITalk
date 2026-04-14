import json
import pytest
from pathlib import Path


SCENARIOS_PATH = Path(__file__).parent.parent.parent / "scripts" / "phase0_scenarios.json"


def load_scenarios() -> list[dict]:
    with open(SCENARIOS_PATH) as f:
        return json.load(f)


def score_production_result(
    llm_output: str,
    lexicon_symbols: set[str],
    marker_symbols: set[str],
) -> float:
    """Return fraction of output characters that are valid lexicon or marker symbols."""
    chars = [ch for ch in llm_output if not ch.isspace()]
    if not chars:
        return 0.0
    valid = sum(1 for ch in chars if ch in lexicon_symbols or ch in marker_symbols)
    return valid / len(chars)


def test_scenarios_file_exists():
    assert SCENARIOS_PATH.exists()


def test_scenarios_have_required_fields():
    scenarios = load_scenarios()
    for s in scenarios:
        assert "id" in s
        assert "type" in s
        assert s["type"] in ("production", "comprehension")
        if s["type"] == "production":
            assert "english_instruction" in s
            assert "expected_lcl_concepts" in s
        else:
            assert "lcl_input" in s
            assert "expected_english_meaning" in s


def test_score_production_all_valid():
    symbols = {"事", "读", "文"}
    markers = {"▲", "△", "◇", "◈"}
    assert score_production_result("事读文", symbols, markers) == 1.0


def test_score_production_with_invalid():
    symbols = {"事", "读", "文"}
    markers = {"▲", "△", "◇", "◈"}
    # 猫 is not a valid symbol
    assert score_production_result("事猫文", symbols, markers) == pytest.approx(2 / 3)


def test_score_production_with_markers():
    symbols = {"文", "多"}
    markers = {"▲", "△", "◇", "◈"}
    assert score_production_result("文▲多", symbols, markers) == 1.0


def test_score_production_empty():
    assert score_production_result("", set(), set()) == 0.0
