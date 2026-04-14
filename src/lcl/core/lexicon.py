import json
from pathlib import Path
from lcl.core.types import Lexicon, LexiconEntry, StructuralMarker


def load_lexicon(path: Path) -> Lexicon:
    with open(path) as f:
        data = json.load(f)

    entries = [
        LexiconEntry(
            rank=e["rank"],
            codepoint=e["codepoint"],
            symbol=e["symbol"],
            concept_id=e["concept_id"],
            english_glosses=e["english_glosses"],
            domain=e["domain"],
            tier=e["tier"],
        )
        for e in data["entries"]
    ]

    markers = {
        name: StructuralMarker(
            name=name,
            codepoint=m["codepoint"],
            symbol=m["symbol"],
        )
        for name, m in data["structural_markers"].items()
    }

    return Lexicon(
        version=data["version"],
        entries=entries,
        structural_markers=markers,
    )
