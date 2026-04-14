from lcl.core.types import Lexicon, ValidationResult


def validate(lcl_string: str, lexicon: Lexicon) -> ValidationResult:
    symbol_lookup = lexicon.symbol_to_entry()
    marker_syms = lexicon.marker_symbols()

    eng_start = lexicon.structural_markers["ENG_START"].symbol
    eng_end = lexicon.structural_markers["ENG_END"].symbol

    known = 0
    unknown: list[str] = []
    markers = 0
    eng_fallbacks = 0
    warnings: list[str] = []
    total = 0

    i = 0
    chars = [ch for ch in lcl_string if not ch.isspace()]

    while i < len(chars):
        ch = chars[i]

        if ch == eng_start:
            # Find matching ENG_END
            j = i + 1
            while j < len(chars) and chars[j] != eng_end:
                j += 1
            if j >= len(chars):
                warnings.append("Unmatched ENG_START marker without ENG_END")
            eng_fallbacks += 1
            markers += 2 if j < len(chars) else 1
            i = j + 1
            continue

        if ch in marker_syms and ch != eng_end:
            markers += 1
            i += 1
            continue

        if ch == eng_end:
            warnings.append("Unexpected ENG_END marker without preceding ENG_START")
            markers += 1
            i += 1
            continue

        total += 1
        if ch in symbol_lookup:
            known += 1
        else:
            unknown.append(ch)

        i += 1

    return ValidationResult(
        is_valid=len(unknown) == 0,
        total_symbols=total,
        known_symbols=known,
        unknown_symbols=unknown,
        marker_count=markers,
        english_fallback_count=eng_fallbacks,
        warnings=warnings,
    )
