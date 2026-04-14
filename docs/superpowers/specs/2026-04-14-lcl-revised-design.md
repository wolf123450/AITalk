# LLM Compressed Lexicon (LCL) — Revised Design Spec

## Overview

A token-efficient symbolic encoding system for LLM-to-LLM communication. LLMs read the lexicon from their system prompt and produce LCL output natively — no external encoder is needed. A companion transliterator enables humans to audit LCL-encoded exchanges.

### Core Premise

The LLM is the encoder. The system prompt is the product. The transliterator is the audit tool.

### Components

1. **The Lexicon** — a Unicode symbol → concept mapping optimized for minimal token count
2. **The System Prompt** — delivers the lexicon and encoding rules to an LLM, enabling it to produce and consume LCL
3. **The Transliterator** — converts LCL-encoded strings back to approximate English for human inspection (lossy gloss output)
4. **The Programmatic Encoder** — optional convenience for converting English text to LCL via exact-match lookup (no NLP)

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Who encodes | The LLM, natively from its system prompt | LLMs handle concept resolution, morphology, and disambiguation better than any programmatic NLP pipeline |
| Compression target | Token count | Minimizes inference cost and context window usage |
| Rare concept fallback | Inline plain English delimited by markers | Simple, unambiguous |
| Initial lexicon scope | Agentic/coding domain first, universal concepts second | Matches the actual use case; Swadesh universals are deferred |
| Human readability | Not a goal for encoding; transliterator handles this | Decouples encoding efficiency from legibility |
| Cross-LLM compatibility | Yes — validated empirically, not pre-audited | CJK common subset is near-certain single-token everywhere; post-hoc validation catches outliers |
| Deployment model | Opt-in per conversation | Activated when token savings matter (long multi-agent chains, high-volume tasks). Also suitable as an inter-agent-only transport where human-facing messages stay in English |
| Language | Python 3.13 with uv | Lightweight tooling, native Unicode support, good MCP SDK |

---

## Architecture

```
[ System Prompt with Lexicon ]
        |
        v
    [ LLM ]  ────produces────>  [ LCL Encoded Output ]
        ^                              |
        |                         (for humans)
   [ LCL Input                   ┌────┴─────┐
   from other LLMs ]             v           v
                              [ CLI ]    [ MCP Server ]
                                 └────┬─────┘
                                      v
                              [ Transliterator ]
                                      v
                           [ English Gloss ]
```

The CLI and MCP server are thin surfaces over the same core library. All transliteration and lookup logic lives in `src/lcl/core/`. The surfaces handle I/O and transport only.

---

## Phases

### Phase 0: Proof of Concept

**Goal:** Answer "can LLMs reliably produce and consume symbolic encoding?" with minimal investment.

**Steps:**

1. Hand-pick ~50 concepts most relevant to agentic coding tasks
   - Task primitives: `task`, `subtask`, `goal`, `step`, `complete`, `fail`, `error`, `retry`, `skip`
   - Tool/resource: `file`, `directory`, `function`, `class`, `variable`, `input`, `output`, `call`, `return`
   - State: `current`, `done`, `pending`, `changed`, `success`, `unknown`
   - Relations/modifiers: `has`, `is`, `of`, `not`, `and`, `or`, `all`, `none`, `many`, `few`
   - Data: `string`, `number`, `list`, `true`, `false`, `null`, `type`, `key`, `value`
2. Assign 50 common CJK characters (high-frequency, near-certain single-token: 人, 大, 中, 上, 下, 出, 入, 行, 目, 文, etc.)
3. Write a system prompt embedding this mini-lexicon with encoding rules
4. Run comprehension tests:
   - **Production test:** Give LLM a natural language instruction + lexicon → ask it to respond in LCL. Parse output against lexicon.
   - **Comprehension test:** Give LLM an LCL-encoded instruction → measure task accuracy vs. plain English baseline.
   - **Resistance test:** Does the LLM resist producing non-Latin output? How much prompting overcomes this?
   - **Compression test:** Measure actual token counts of LCL vs. English for equivalent content.

**Test targets:**
- Claude (API)
- GPT-4o (API)
- Local models via Ollama (LLaMA 3, Mistral, Gemma, etc.)

**Gate criteria — all three must pass to proceed:**

| Criterion | Pass Threshold |
|---|---|
| LLM produces valid LCL | ≥90% of output symbols are valid lexicon entries |
| LLM comprehends LCL input | ≥85% task accuracy vs. plain English baseline |
| Net token savings positive | Compression ratio > 1.0 after lexicon system prompt cost |

**If a criterion fails:**

- LLM resists producing symbols → test Latin syllable codes as fallback encoding
- LLM can't comprehend LCL → lexicon format or concept granularity needs rework
- Net savings negative → lexicon too large for message volume; reduce scope or switch to reference-mode (lexicon via tool call)

**Output:** `tests/phase0/results.md` — gate decision document with raw data.

---

### Phase 1: Lexicon Construction

**Goal:** Build the full lexicon, informed by Phase 0 findings.

**Concept tiers:**

- **Tier 1 (~50 concepts):** The Phase 0 set, refined based on test results
- **Tier 2 (~100-150 concepts):** Remaining agentic/coding vocabulary:
  - Code concepts: `test`, `build`, `deploy`, `debug`, `refactor`, `lint`, `compile`, `run`, `log`, `assert`
  - Agent concepts: `agent`, `tool`, `context`, `memory`, `prompt`, `response`, `token`, `cost`, `limit`, `timeout`
  - Control flow: `if`, `else`, `loop`, `break`, `continue`, `return`, `throw`, `catch`
  - Relations: `depends-on`, `calls`, `produces`, `consumes`, `is-a`, `has-a`, `part-of`
  - Quantifiers: `more`, `less`, `equal`, `greater`, `some`
- **Tier 3 (future):** Universal reasoning vocabulary — useful Swadesh-type concepts (pronouns, basic actions, spatial terms) that appear in LLM reasoning. Not body parts or natural phenomena.

**Symbol space:**

- Primary: CJK Unified Ideographs (common subset, ~500 characters from U+4E00–U+9FFF)
- Characters selected for high training frequency (near-certain single-token across tokenizers)
- Post-hoc token count validation against `tiktoken` (cl100k_base, o200k_base) and Ollama-hosted models

**Structural markers (Geometric Shapes block):**

| Marker | Symbol | Purpose |
|---|---|---|
| `MOD` | ▲ (U+25B2) | Modifier follows: `FILE MOD LARGE` = "large file" |
| `NEG` | △ (U+25B3) | Negation: `NEG COMPLETE` = "not done" |
| `ENG_START` | ◇ (U+25C7) | English fallback begins |
| `ENG_END` | ◈ (U+25C8) | English fallback ends |

SOT/EOT and Q markers deferred — add only if Phase 0 reveals the LLM struggles without explicit boundary/query markers.

**Compound rules:**

When a concept is not in the lexicon:
1. `HEAD + MOD + MODIFIER` for adjectival modification
2. `ACTION + TARGET` for verb-object (positional, no marker)
3. `ENG_START ... ENG_END` for anything that can't be composed

Compounds are generated by the LLM at production time and resolved by the transliterator at decode time. They are not pre-enumerated.

**Output:** `data/lexicon.json`

```json
{
  "version": "0.1.0",
  "entries": [
    {
      "rank": 1,
      "codepoint": "U+4EBA",
      "symbol": "人",
      "concept_id": "PERSON",
      "english_glosses": ["person", "human", "individual"],
      "domain": "universal",
      "tier": 1
    }
  ],
  "structural_markers": {
    "MOD": { "codepoint": "U+25B2", "symbol": "▲" },
    "NEG": { "codepoint": "U+25B3", "symbol": "△" },
    "ENG_START": { "codepoint": "U+25C7", "symbol": "◇" },
    "ENG_END": { "codepoint": "U+25C8", "symbol": "◈" }
  }
}
```

---

### Phase 2: System Prompt Engineering

**Goal:** Optimize how the lexicon is delivered to LLMs.

**Tasks:**

1. Design the most token-efficient prompt format for embedding the lexicon
   - Test compact notation: `人=person 大=big 中=middle`
   - Test structured notation: `人:person,human | 大:big,large`
   - Test table format vs. inline list
2. Measure the lexicon's own token cost at various sizes (50, 100, 200, 400 concepts)
3. Compute the **break-even point**: how many messages in a conversation before LCL's compression savings exceed the system prompt cost of embedding the lexicon
4. Test reference-mode: lexicon delivered via MCP tool call instead of system prompt. Compare LLM compliance vs. embedded mode.
5. Iterate on encoding rules section — minimize rule verbosity while maintaining LLM compliance

**Output:** `prompts/full-lexicon.md`, `prompts/reference-mode.md`

---

### Phase 3: Transliterator + CLI

**Goal:** Build the human audit tool.

**Transliterator:**

```python
class TransliterateResult:
    english: str          # approximate English gloss
    confidence: float     # 0–1, portion resolved from lexicon vs. English fallback
    unknown_symbols: list[str]  # codepoints not found in lexicon
    warnings: list[str]   # e.g. "compound resolution ambiguous"

def transliterate(lcl: str) -> TransliterateResult:
    ...
```

Pipeline:
1. Segment input into individual codepoints / marker sequences
2. Look up each codepoint in lexicon → primary english gloss
3. Interpret structural markers (MOD → adjective order, NEG → "not X", ENG → passthrough)
4. Assemble naive English gloss (word salad, not grammatical prose)
5. Return result with metadata

**Encoder (optional):**

```python
def encode(text: str) -> str:
    ...
```

Exact-match only — looks up each whitespace-delimited word in the lexicon's english_glosses. No stemming, no WSD. Words not found are wrapped in ENG delimiters.

**CLI:**

```
lcl decode <lcl-string>          # primary use case
  --stdin                        # read from stdin
  --json                         # full TransliterateResult

lcl encode <text>                # optional convenience
  --stdin
  --json

lcl lexicon list                 # pretty-print the lexicon
lcl lexicon stats                # concept count, token cost of lexicon itself
lcl lexicon prompt               # output the system prompt template

lcl validate <lcl-string>        # check all symbols against lexicon
```

---

### Phase 4: MCP Server

**Goal:** Expose transliteration and lexicon as MCP tools for agent integration.

**Server name:** `lcl`

**Tools:**

| Tool | Description |
|---|---|
| `lcl_decode` | Transliterate LCL → English gloss |
| `lcl_encode` | Optional: English → LCL (exact-match) |
| `lcl_validate` | Check LCL string validity, flag unknown symbols |
| `lcl_lexicon_info` | Lexicon metadata: version, concept count, domains, token cost |
| `lcl_get_prompt` | Return system prompt template with embedded lexicon |

**MCP configuration:**
```json
{
  "mcpServers": {
    "lcl": {
      "command": "uv",
      "args": ["run", "lcl-mcp"]
    }
  }
}
```

---

### Phase 5: Evaluation

**Goal:** Formal benchmarking on the full lexicon.

| Benchmark | Target |
|---|---|
| Compression ratio (agentic tasks) | >40% token reduction |
| Round-trip fidelity (encode → transliterate) | >0.80 cosine similarity |
| LLM task accuracy in LCL vs. English | <5% degradation |
| Cross-tokenizer token count variance | <10% |
| Break-even conversation length | Document the message count at which LCL pays for system prompt cost |

---

## Repository Structure

```
lcl/
├── data/
│   └── lexicon.json
├── src/
│   └── lcl/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── transliterator.py
│       │   ├── encoder.py
│       │   ├── validator.py
│       │   ├── lexicon.py
│       │   └── types.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py
│       └── mcp/
│           ├── __init__.py
│           └── server.py
├── prompts/
│   ├── full-lexicon.md
│   └── reference-mode.md
├── tests/
│   ├── phase0/
│   │   └── results.md
│   └── ...
├── benchmarks/
│   └── eval.py
├── pyproject.toml
└── README.md
```

## Tech Stack

- **Language:** Python 3.13
- **Package/env management:** uv
- **CLI:** click or typer
- **MCP:** mcp (official Python SDK)
- **Testing:** pytest
- **Data:** JSON
- **Local LLM testing:** Ollama (LLaMA 3, Mistral, Gemma, etc.)
- **API LLM testing:** Claude (Anthropic API), GPT-4o (OpenAI API)

## Implementation Risks

1. **LLM resistance to symbolic output.** Models may resist producing non-Latin characters even when instructed. Phase 0 tests this directly. If resistance is high, Latin syllable codes (e.g., `za`, `bi`, `ko`) are the fallback — at a compression cost.

2. **Lexicon system prompt cost.** The lexicon itself consumes tokens. At 200 entries × ~5 tokens/entry in compact format = ~1000 tokens. This must be recouped through message compression. The break-even analysis in Phase 2 quantifies this tradeoff.

3. **Concept granularity.** A single concept per symbol may be too coarse for some agentic contexts. Compound rules must handle the gaps. Phase 0 will reveal whether the ~50-concept tier is sufficient or too sparse.

4. **Cross-tokenizer fragmentation.** Some CJK codepoints may fragment into multiple tokens on certain tokenizers. Post-hoc validation catches this, but fixing it means reassigning affected symbols — which is cheap if done before external adoption.

## Build Order

1. Hand-curate 50 Phase 0 concepts, assign CJK symbols
2. Write Phase 0 system prompt
3. Run LLM comprehension tests (Ollama local + API)
4. Gate decision: proceed, pivot, or abandon
5. Expand to full ~200-concept lexicon, produce `lexicon.json`
6. System prompt engineering and break-even analysis
7. Build transliterator core (lookup-based)
8. Wire into CLI (`lcl decode`) — first usable artifact
9. Add optional encoder and validator
10. Build MCP server
11. Run formal benchmarks
12. Package CLI and MCP server for distribution
