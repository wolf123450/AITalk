import pytest
from pathlib import Path
from lcl.core.lexicon import load_lexicon
from lcl.core.types import Lexicon, LexiconEntry, StructuralMarker


def test_load_lexicon_from_file(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    assert isinstance(lexicon, Lexicon)
    assert lexicon.version == "0.1.0-phase0"
    assert len(lexicon.entries) == 50


def test_load_lexicon_entries_are_correct(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    first = lexicon.entries[0]
    assert first.rank == 1
    assert first.symbol == "事"
    assert first.concept_id == "TASK"
    assert "task" in first.english_glosses
    assert first.domain == "agentic"
    assert first.tier == 1


def test_load_lexicon_structural_markers(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    assert "MOD" in lexicon.structural_markers
    assert lexicon.structural_markers["MOD"].symbol == "▲"
    assert "NEG" in lexicon.structural_markers
    assert "ENG_START" in lexicon.structural_markers
    assert "ENG_END" in lexicon.structural_markers


def test_symbol_to_entry_lookup(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    lookup = lexicon.symbol_to_entry()
    assert "事" in lookup
    assert lookup["事"].concept_id == "TASK"
    assert "读" in lookup
    assert lookup["读"].concept_id == "READ"


def test_concept_to_entry_lookup(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    lookup = lexicon.concept_to_entry()
    assert "TASK" in lookup
    assert lookup["TASK"].symbol == "事"


def test_gloss_to_entry_lookup(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    lookup = lexicon.gloss_to_entry()
    assert "task" in lookup
    assert lookup["task"].concept_id == "TASK"
    assert "job" in lookup
    assert lookup["job"].concept_id == "TASK"


def test_gloss_lookup_is_case_insensitive(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    lookup = lexicon.gloss_to_entry()
    assert "Task" not in lookup  # stored lowercase
    assert "task" in lookup


def test_marker_symbols(data_dir: Path):
    lexicon = load_lexicon(data_dir / "phase0-lexicon.json")
    markers = lexicon.marker_symbols()
    assert "▲" in markers
    assert "△" in markers
    assert "◇" in markers
    assert "◈" in markers
    assert len(markers) == 4
