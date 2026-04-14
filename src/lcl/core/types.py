from dataclasses import dataclass, field


@dataclass(frozen=True)
class LexiconEntry:
    rank: int
    codepoint: str  # e.g. "U+4E8B"
    symbol: str  # e.g. "事"
    concept_id: str  # e.g. "TASK"
    english_glosses: list[str]  # e.g. ["task", "job"]
    domain: str  # "agentic" | "universal"
    tier: int  # 1, 2, or 3


@dataclass(frozen=True)
class StructuralMarker:
    name: str  # e.g. "MOD"
    codepoint: str  # e.g. "U+25B2"
    symbol: str  # e.g. "▲"


@dataclass(frozen=True)
class Lexicon:
    version: str
    entries: list[LexiconEntry]
    structural_markers: dict[str, StructuralMarker]

    def symbol_to_entry(self) -> dict[str, LexiconEntry]:
        return {e.symbol: e for e in self.entries}

    def concept_to_entry(self) -> dict[str, LexiconEntry]:
        return {e.concept_id: e for e in self.entries}

    def gloss_to_entry(self) -> dict[str, LexiconEntry]:
        result: dict[str, LexiconEntry] = {}
        for entry in self.entries:
            for gloss in entry.english_glosses:
                result[gloss.lower()] = entry
        return result

    def marker_symbols(self) -> set[str]:
        return {m.symbol for m in self.structural_markers.values()}


@dataclass
class ValidationResult:
    is_valid: bool
    total_symbols: int
    known_symbols: int
    unknown_symbols: list[str]
    marker_count: int
    english_fallback_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class TransliterateResult:
    english: str
    confidence: float  # 0–1
    unknown_symbols: list[str]
    warnings: list[str] = field(default_factory=list)
