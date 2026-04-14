# LLM Compressed Lexicon (LCL) — Project Plan

## Project Overview

Design and implement a token-efficient symbolic encoding system for LLM-to-LLM communication, with a companion transliterator for human analysis. The encoding is not intended to be human-readable; correctness and token efficiency are the only design constraints on the encoding itself.

The system consists of three components:

1. **The Lexicon** — a Unicode symbol → concept mapping, assigned by cross-linguistic concept frequency, optimized for minimal token count
2. **The Encoder** — converts plain English (or structured data) into LCL-encoded strings
3. **The Transliterator** — converts LCL-encoded strings back to approximate English for human inspection (lossy, gloss-quality output is acceptable)

---

## Core Design Decisions (Locked)

| Decision | Choice | Rationale |
|---|---|---|
| Compression target | Token count | Minimizes LLM inference cost and context window usage |
| Rare concept fallback | Inline plain English | Simple, no ambiguity, avoids over-engineering edge cases |
| Initial lexicon scope | Swadesh universal core + coding/agentic domain | Covers general reasoning primitives and software task vocabulary |
| Human readability | Not a goal for encoding; transliterator handles this | Decouples encoding efficiency from legibility |
| Cross-LLM compatibility | Yes — no tokenizer-specific assumptions | Unicode codepoints selected to be single tokens across major tokenizers |

---

## Architecture

```
[ Plain English / Structured Input ]
            |
     ┌──────┴──────┐
     v             v
  [ CLI ]       [ MCP Server ]          ← access surfaces
     └──────┬──────┘
            v
       [ Encoder ]                      ← core library
            |
            v
  [ LCL Encoded String ]  <-- what LLMs send/receive
            |
       (for humans)
     ┌──────┴──────┐
     v             v
  [ CLI ]       [ MCP Server ]
     └──────┬──────┘
            v
     [ Transliterator ]                 ← core library
            v
  [ Approximate English gloss ]
```

The CLI and MCP server are thin surfaces over the same core library (`src/core/`). All encoding and transliteration logic lives in core; the surfaces handle I/O formatting and transport only.

The LLM is expected to receive the lexicon definition (or a compressed reference to it) in its system prompt, enabling it to both read and produce LCL-encoded output.

---

## Phase 1: Research & Data Collection

### 1.1 Concept Frequency Baseline

**Goal:** Produce a ranked list of ~600–1000 concepts by cross-linguistic communicative frequency.

**Data sources to acquire:**

- **Swadesh 207-item list** — baseline universal vocabulary (body parts, basic actions, pronouns, natural phenomena). Available as structured data from Wiktionary or CLLD.
- **Concepticon** (`concepticon.clld.org`) — maps concept labels across 300+ wordlists. Download the concept set data and compute cross-list frequency (how many independent wordlists include each concept).
- **SUBTLEX corpora** — subtitle-derived word frequencies for English, German, Dutch, Chinese, Spanish. Use to validate that high-frequency concepts in Concepticon also have high token frequency in English.
- **Coding/agentic domain vocabulary** — manually curated list of ~150–200 concepts specific to software development and agentic task execution. See Section 1.3.

**Output:** A single ranked `concepts.json` file with fields:
```json
{
  "rank": 1,
  "concept_id": "PERSON",
  "swadesh": true,
  "concepticon_frequency": 287,
  "english_gloss": ["person", "human", "man", "woman"],
  "notes": ""
}
```

### 1.2 Tokenizer Audit

**Goal:** Identify which Unicode codepoints and short codepoint sequences are reliably single tokens across major LLM tokenizers.

**Tokenizers to audit:**
- `cl100k_base` (GPT-4, GPT-4o)
- `o200k_base` (GPT-4o-mini, o-series)
- LLaMA 3 tokenizer (SentencePiece)
- Mistral tokenizer
- Claude's tokenizer (via `anthropic-tokenizer` or empirical testing)

**Method:**
- For each candidate Unicode block (see Section 2.1), encode a sequence of individual codepoints through each tokenizer and record token boundaries.
- A codepoint is "safe" if it maps to exactly 1 token in all audited tokenizers.
- A codepoint is "acceptable" if it maps to 1 token in 4/5 tokenizers.
- Document unsafe codepoints explicitly.

**Output:** `tokenizer-audit.json` mapping each candidate codepoint range to its token-safety classification.

### 1.3 Coding/Agentic Domain Vocabulary

**Goal:** Curate the ~150–200 most important concepts for software agent communication not already covered by Swadesh.

**Concept categories to cover:**

- **Task primitives:** task, subtask, goal, plan, step, complete, fail, block, retry, skip, delegate
- **State:** current, previous, next, done, pending, error, success, unknown, changed
- **Tool/resource:** file, directory, function, class, variable, input, output, argument, return, call, import
- **Code concepts:** test, build, deploy, debug, refactor, lint, compile, run, log, assert
- **Agent concepts:** agent, tool, context, memory, prompt, response, token, cost, limit, timeout
- **Data types:** string, number, boolean, list, dict, null, type, schema, key, value
- **Control flow:** if, else, loop, break, continue, return, throw, catch
- **Relations:** depends-on, calls, produces, consumes, is-a, has-a, part-of
- **Quantifiers/modifiers:** many, few, all, none, some, more, less, equal, greater, less-than

**Output:** Added to `concepts.json` with `"domain": "coding"` flag.

---

## Phase 2: Unicode Symbol Space Design

### 2.1 Candidate Unicode Blocks

The goal is to find Unicode ranges where:
- Individual characters are single tokens in all major tokenizers
- Characters are visually distinct (aids debugging)
- Characters are not commonly used in natural English or code (avoids collision)

**Priority candidate blocks to evaluate:**

| Block | Range | Characters | Notes |
|---|---|---|---|
| CJK Unified Ideographs (common) | U+4E00–U+9FFF | ~20,000 | Many are single tokens; visually distinct; high risk of collision with actual CJK content |
| Hangul Syllables | U+AC00–U+D7A3 | 11,172 | Likely single tokens; rarely appear in English/code context |
| Mathematical symbols | U+2200–U+22FF | 256 | Already used in math; some single-token |
| Enclosed Alphanumerics | U+2460–U+24FF | ~160 | Circled numbers/letters; likely single tokens |
| Geometric Shapes | U+25A0–U+25FF | 96 | Visually distinct; mostly single tokens |
| Miscellaneous Symbols | U+2600–U+26FF | 256 | Emojis adjacent; mixed token behavior |
| Braille Patterns | U+2800–U+28FF | 256 | Compact, rarely used in text, likely single-token |
| Box Drawing | U+2500–U+257F | 128 | Used in terminals; largely single-token |
| Private Use Area | U+E000–U+F8FF | 6,400 | Explicitly reserved; tokenizer behavior unpredictable — audit first |

**Recommendation:** Begin audit with Hangul Syllables (large space, minimal collision risk) and Braille Patterns (compact, visually distinct). Use Geometric Shapes for structural/grammatical markers.

### 2.2 Symbol Assignment Strategy

Assign symbols by concept frequency rank after the tokenizer audit confirms available safe codepoints:

- **Tier 1 (ranks 1–100):** Highest-frequency universal concepts. Assign single codepoints from the most token-safe block.
- **Tier 2 (ranks 101–400):** Common concepts. Assign single codepoints from secondary safe block.
- **Tier 3 (ranks 401–800):** Less frequent / domain-specific. Assign single codepoints from tertiary block.
- **Overflow / compounds:** Concepts that don't fit get expressed as two-symbol compounds (Tier 1 + Tier 1 modifier pattern).

### 2.3 Structural / Grammatical Markers

A small reserved set of symbols (not concept-bearing) to handle syntax:

| Marker | Purpose | Example |
|---|---|---|
| `⟨SOT⟩` | Start of thought / sentence boundary | Separates logical units |
| `⟨EOT⟩` | End of thought | Closes a logical unit |
| `⟨MOD⟩` | Modifier follows (adjective/adverb role) | `PERSON MOD SMALL` = small person |
| `⟨NEG⟩` | Negation | `NEG COMPLETE` = not done |
| `⟨Q⟩` | Query marker | signals a question |
| `⟨ENG⟩` | English fallback start | next token(s) are plain English |
| `⟨/ENG⟩` | English fallback end | return to LCL |

These should be assigned codepoints from Geometric Shapes or Box Drawing — visually distinct from concept symbols.

---

## Phase 3: Lexicon Construction

### 3.1 Schema

The lexicon is a JSON file (`lexicon.json`) with the following structure:

```json
{
  "version": "0.1.0",
  "token_audit_date": "2025-XX-XX",
  "entries": [
    {
      "rank": 1,
      "codepoint": "U+AC00",
      "symbol": "가",
      "concept_id": "PERSON",
      "english_glosses": ["person", "human", "individual"],
      "swadesh": true,
      "domain": "universal",
      "notes": "Covers human/person/individual; gender-neutral"
    }
  ],
  "structural_markers": {
    "SOT": "U+25A0",
    "EOT": "U+25A1",
    "MOD": "U+25B2",
    "NEG": "U+25B3",
    "Q": "U+25C6",
    "ENG_START": "U+25C7",
    "ENG_END": "U+25C8"
  }
}
```

### 3.2 Compound Rules

When a concept is not in the lexicon, compose it from existing symbols using these precedence rules:

1. `HEAD + MOD_MARKER + MODIFIER` for adjectival modification
2. `ACTION + TARGET` for verb-object constructs (no marker needed, positional)
3. `ENG_START ... ENG_END` for anything that can't be composed cleanly

Compounds are not pre-enumerated in the lexicon — they are generated at encode time and resolved at transliterate time.

---

## Phase 4: Encoder Implementation

### 4.1 Encoder Interface

```typescript
interface LCLEncoder {
  encode(input: string, options?: EncodeOptions): string;
  encodeStructured(input: Record<string, unknown>): string;
}

interface EncodeOptions {
  fallbackToEnglish: boolean;  // default true
  includeSOT: boolean;          // wrap output in SOT/EOT markers
  domain: 'universal' | 'coding' | 'auto';  // hint for concept lookup
}
```

### 4.2 Encoding Pipeline

```
Input string
    |
    v
[ NLP tokenization ] — split into words/phrases
    |
    v
[ Concept resolution ] — map words to concept_ids via english_glosses lookup
    |                     (fuzzy match for morphological variants: "running" → RUN)
    v
[ Symbol assignment ] — look up codepoint for each concept_id
    |
    v
[ Compound generation ] — for multi-word concepts, apply compound rules
    |
    v
[ Fallback wrapping ] — unresolved tokens wrapped in ENG_START...ENG_END
    |
    v
[ Structural markers ] — insert SOT/EOT, handle MOD/NEG markers
    |
    v
LCL-encoded string
```

### 4.3 Concept Resolution Notes

- Stemming/lemmatization before lookup (e.g., Porter stemmer or similar)
- Compound English phrases should be tried before individual words ("file system" → FILE_SYSTEM before FILE + SYSTEM)
- Ambiguous words (polysemes) resolved by domain hint and surrounding context
- Proper nouns, numbers, code identifiers always fall back to English

---

## Phase 5: Transliterator Implementation

### 5.1 Transliterator Interface

```typescript
interface LCLTransliterator {
  transliterate(lcl: string): TransliterateResult;
}

interface TransliterateResult {
  english: string;       // approximate English gloss
  confidence: number;    // 0–1, how much fell back to English vs. was resolved
  unknownSymbols: string[];  // codepoints not found in lexicon
  warnings: string[];    // e.g. "compound resolution ambiguous"
}
```

### 5.2 Transliteration Pipeline

```
LCL-encoded string
    |
    v
[ Codepoint segmentation ] — split into individual codepoints / marker sequences
    |
    v
[ Symbol lookup ] — map each codepoint to concept_id + primary english_gloss
    |
    v
[ Structural interpretation ] — apply SOT/EOT as sentence breaks,
    |                            MOD as adjective order, NEG as "not X",
    |                            Q as "?" suffix, ENG passthrough
    v
[ English assembly ] — naive gloss assembly (no grammar synthesis)
    |
    v
[ Output ] — approximate English string + metadata
```

**Important:** The transliterator does NOT attempt to produce grammatically correct English. It produces a word-salad gloss sufficient for human comprehension. Example:

```
LCL:  ■ 가 ▲ 소 △ COMPLETE ■
Gloss: [person] [MOD: small] [NOT complete]
Human readable: "small person, not complete"
```

---

## Phase 6: System Prompt Template

For LLMs to use LCL, they need the lexicon embedded in (or referenced from) their system prompt.

### 6.1 Full Lexicon Prompt Mode

Embed the full lexicon as a structured block. Suitable for models with large context windows.

```
You communicate using LCL (LLM Compressed Lexicon).
LEXICON:
[symbol] = [concept] | [symbol] = [concept] | ...
RULES:
- Use LCL symbols for all concepts in the lexicon
- For concepts not in the lexicon, wrap in [ENG_START]...[ENG_END]
- [MOD] precedes a modifier: HEAD [MOD] MODIFIER
- [NEG] negates the following symbol
- Separate logical units with [SOT]...[EOT]
```

### 6.2 Reference Prompt Mode

For models that can retrieve the lexicon externally (via tool call or memory), only the structural rules are embedded in the system prompt, and the lexicon is fetched on demand.

---

## Phase 7: Evaluation

### 7.1 Compression Ratio Benchmark

For a standard test corpus (mix of agentic task descriptions, reasoning chains, code review comments):

- Measure token count of original English
- Measure token count of LCL-encoded version
- Report compression ratio per category

Target: >40% token reduction on in-domain content (agentic/coding tasks).

### 7.2 Round-Trip Fidelity

Encode a set of English sentences → LCL → transliterate back → measure semantic similarity to original (using embedding cosine similarity, not exact match).

Target: >0.85 cosine similarity on Swadesh-domain sentences; >0.75 on coding-domain.

### 7.3 LLM Comprehension Test

Give an LLM a system prompt containing the lexicon and a set of LCL-encoded instructions. Measure task completion accuracy vs. plain English baseline.

Target: <5% degradation in task accuracy vs. plain English.

### 7.4 Cross-Tokenizer Token Count Validation

Re-run token count benchmark across all 5 audited tokenizers. Flag any LCL sequences where cross-tokenizer variance exceeds 10% (indicates tokenizer-unsafe codepoint).

---

## Deliverables

| Deliverable | Format | Phase |
|---|---|---|
| `concepts.json` | JSON | 1 |
| `tokenizer-audit.json` | JSON | 1 |
| `lexicon.json` | JSON | 3 |
| `lexicon.md` | Human-readable reference | 3 |
| Core encoder/transliterator library | TypeScript | 4–5 |
| CLI tool (`lcl`) | TypeScript, compiled binary via `pkg` or `tsx` | 4–5 |
| MCP server (`lcl-mcp`) | TypeScript, MCP SDK | 4–5 |
| System prompt templates | Markdown | 6 |
| Benchmark results | JSON + Markdown report | 7 |

---

## Implementation Notes for Claude Code

### Suggested Tech Stack

- **Language:** TypeScript (Node.js) — good Unicode handling, easy to integrate with LLM APIs
- **NLP:** `compromise` or `natural` for stemming/lemmatization (lightweight, no Python dep)
- **Data:** JSON throughout; no database needed at this scale
- **CLI:** `commander` for argument parsing; distributed as a compiled binary via `pkg` or run directly with `tsx`
- **MCP:** `@modelcontextprotocol/sdk` (official MCP TypeScript SDK)
- **Testing:** Vitest

### Repository Structure

```
lcl/
├── data/
│   ├── concepts.json            # ranked concept list (output of Phase 1)
│   ├── tokenizer-audit.json     # codepoint safety map (output of Phase 1)
│   └── lexicon.json             # final symbol assignments (output of Phase 3)
├── src/
│   ├── core/
│   │   ├── encoder.ts           # encode(): English → LCL
│   │   ├── transliterator.ts    # transliterate(): LCL → English gloss
│   │   ├── lexicon.ts           # lexicon loading + lookup utilities
│   │   └── types.ts             # shared types
│   ├── cli/
│   │   └── index.ts             # CLI entry point (lcl encode / lcl decode / lcl audit)
│   └── mcp/
│       └── server.ts            # MCP server entry point
├── scripts/
│   ├── build-concepts.ts        # Phase 1: pull + merge Concepticon + Swadesh data
│   ├── audit-tokenizers.ts      # Phase 1: tokenizer safety audit
│   └── assign-symbols.ts        # Phase 3: auto-assign codepoints by rank
├── prompts/
│   ├── full-lexicon.md
│   └── reference-mode.md
├── benchmarks/
│   └── eval.ts
└── README.md
```

### CLI Design

The CLI binary is named `lcl` and exposes the following subcommands:

```
lcl encode [options] <text>
  --domain <universal|coding|auto>   concept resolution hint (default: auto)
  --stdin                            read input from stdin instead of argument
  --json                             output as JSON with metadata

lcl decode <lcl-string>
  --stdin                            read input from stdin
  --json                             output full TransliterateResult as JSON

lcl audit
  # runs tokenizer safety audit on all configured Unicode blocks
  # outputs tokenizer-audit.json

lcl lexicon list
  # pretty-prints the current lexicon

lcl lexicon stats
  # prints lexicon coverage, compression ratio estimates, token safety summary
```

**Usage examples:**
```bash
# Encode a task description
lcl encode --domain coding "run the test suite and report failures"

# Decode for human inspection
lcl decode "가▲소△..." 

# Pipeline usage
cat task.txt | lcl encode --stdin | some-agent | lcl decode --stdin

# JSON output for programmatic use
lcl encode --json "process the file" | jq .encoded
```

### MCP Server Design

The MCP server (`lcl-mcp`) exposes the encoder and transliterator as MCP tools, making them directly callable by Claude Code, Claude Desktop, or any MCP-compatible agent host.

**Server name:** `lcl`

**Tools exposed:**

```
lcl_encode
  Description: Encode plain English text into LCL (LLM Compressed Lexicon) format
               to minimize token count for LLM-to-LLM communication.
  Input:
    text: string          — the English text to encode
    domain: string        — "universal" | "coding" | "auto" (default: "auto")
  Output:
    encoded: string       — LCL-encoded string
    original_tokens: number
    encoded_tokens: number
    compression_ratio: number
    fallback_count: number  — number of concepts that fell back to plain English

lcl_decode
  Description: Transliterate an LCL-encoded string back to approximate English
               for human inspection. Output is a gloss, not grammatical prose.
  Input:
    lcl: string           — LCL-encoded string to transliterate
  Output:
    english: string       — approximate English gloss
    confidence: number    — 0–1
    unknown_symbols: string[]
    warnings: string[]

lcl_lexicon_info
  Description: Returns metadata about the current lexicon, including version,
               concept count, coverage domains, and token safety summary.
  Input: (none)
  Output:
    version: string
    concept_count: number
    domains: string[]
    token_safe_ratio: number
    audit_date: string
```

**MCP server configuration** (for Claude Desktop / Claude Code `mcp.json`):
```json
{
  "mcpServers": {
    "lcl": {
      "command": "node",
      "args": ["/path/to/lcl/dist/mcp/server.js"]
    }
  }
}
```

Or if distributed as an npm package:
```json
{
  "mcpServers": {
    "lcl": {
      "command": "npx",
      "args": ["lcl-mcp"]
    }
  }
}
```

### Key Implementation Risks

1. **Tokenizer behavior for novel Unicode:** Some tokenizers handle unseen codepoints by falling back to byte-level encoding (multiple tokens per character). The audit in Phase 1.2 is not optional — skipping it will invalidate compression ratio claims.

2. **LLM instruction-following with symbolic encoding:** Models may resist producing non-Latin output even when instructed. This needs empirical testing early. If resistance is high, a Latin-character encoding (using short nonsense syllables assigned by frequency rank, like `za`, `bi`, `ko`...) may be a necessary fallback — at a cost to compression ratio.

3. **Concept granularity:** The Swadesh list is coarse (e.g., "person" covers a lot). The coding domain may need finer distinctions than a single concept per symbol supports. Compound rules must be well-defined before the encoder is built.

4. **Encoder ambiguity:** English is highly polysemous. "run" means execute (code), move fast, manage (a business), and many more. Domain hints help but don't solve this. The encoder should log ambiguous resolutions for later lexicon refinement.

### Suggested Build Order

1. Build `concepts.json` manually for the first 100 concepts (don't wait for full Concepticon pipeline)
2. Run tokenizer audit on Hangul block as proof of concept
3. Assign symbols for top 100 concepts, build minimal `lexicon.json`
4. Build transliterator core first (simpler, lookup-only) — use it to validate the lexicon feels right
5. Wire transliterator into CLI (`lcl decode`) — first usable artifact
6. Build encoder core with just exact-match concept resolution
7. Wire encoder into CLI (`lcl encode`) — full round-trip testable from command line
8. Add stemming/fuzzy match to encoder core
9. Build MCP server wrapping encode + decode + lexicon_info tools
10. Run compression benchmarks
11. Expand lexicon to full scope based on benchmark gaps
12. Package CLI as distributable binary; publish MCP server as npm package
