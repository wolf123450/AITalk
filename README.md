# AITalk — LLM Compressed Lexicon (LCL)

A token-efficient symbolic encoding system for LLM-to-LLM communication. LCL maps high-frequency concepts to single Unicode codepoints (selected for cross-tokenizer safety), allowing LLMs to exchange information at a fraction of the token cost of plain English.

The encoding is not intended to be human-readable. A companion transliterator converts LCL back to approximate English gloss for debugging and inspection.

## Components

| Component | Description |
|-----------|-------------|
| **Lexicon** | Unicode symbol → concept mapping, assigned by cross-linguistic concept frequency |
| **Encoder** | Converts plain English or structured data into LCL-encoded strings |
| **Transliterator** | Converts LCL back to approximate English gloss (lossy, for human inspection) |
| **CLI** (`lcl`) | `lcl encode` / `lcl decode` / `lcl audit` |
| **MCP Server** | Exposes encode/decode/lexicon-info as MCP tools for Claude Code and Claude Desktop |

## How It Works

Concepts are ranked by cross-linguistic communicative frequency (Swadesh universal core + coding/agentic domain vocabulary) and assigned to single Unicode codepoints that are confirmed single tokens across major LLM tokenizers (GPT-4, LLaMA 3, Mistral, Claude). Rare or out-of-lexicon concepts fall back to inline plain English wrapped in delimiters.

```
lcl encode --domain coding "run the test suite and report failures"
# → 가▲소△...

lcl decode "가▲소△..."
# → [run] [test] [suite] [report] [failure]

# Pipeline usage
cat task.txt | lcl encode --stdin | some-agent | lcl decode --stdin
```

## Architecture

```
[ Plain English / Structured Input ]
            |
     ┌──────┴──────┐
     v             v
  [ CLI ]       [ MCP Server ]
     └──────┬──────┘
            v
       [ Encoder ]  →  LCL Encoded String
            |
     [ Transliterator ]  →  Approximate English gloss
```

## Status

Early implementation. Core library (`src/lcl/`) exists with lexicon, token, type, and validator modules. Full encoder/transliterator CLI and MCP server are planned. See `llm-lexicon-plan.md` for the full design spec.

## Design Goals

- **Token reduction target:** >40% on agentic/coding tasks
- **Cross-tokenizer safety:** Codepoints confirmed single-token on GPT-4, LLaMA 3, Mistral, Claude
- **Round-trip fidelity target:** >0.85 cosine similarity on Swadesh-domain sentences
- **LLM task accuracy degradation:** <5% vs. plain English baseline
