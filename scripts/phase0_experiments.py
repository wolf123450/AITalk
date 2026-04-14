#!/usr/bin/env python3
"""Phase 0 experiment runner — tests LLM comprehension of LCL encoding.

Usage:
    uv run python scripts/phase0_experiments.py --model llama3.2:3b
    uv run python scripts/phase0_experiments.py --model mistral:7b --host http://localhost:11434

Requires Ollama to be running and the model to be pulled.
"""

import argparse
import json
from pathlib import Path

import ollama

from lcl.core.lexicon import load_lexicon
from lcl.core.tokens import count_tokens

DATA_DIR = Path(__file__).parent.parent / "data"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
SCENARIOS_PATH = Path(__file__).parent / "phase0_scenarios.json"


def load_system_prompt() -> str:
    return (PROMPTS_DIR / "phase0-system.md").read_text()


def load_scenarios() -> list[dict]:
    with open(SCENARIOS_PATH) as f:
        return json.load(f)


def run_production_test(
    scenario: dict,
    model: str,
    system_prompt: str,
    client: ollama.Client,
) -> dict:
    user_msg = (
        f"Translate this to LCL (respond ONLY with LCL symbols, no English): "
        f"{scenario['english_instruction']}"
    )
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    llm_output = response.message.content.strip()

    return {
        "scenario_id": scenario["id"],
        "input": scenario["english_instruction"],
        "llm_output": llm_output,
        "expected_concepts": scenario["expected_lcl_concepts"],
    }


def run_comprehension_test(
    scenario: dict,
    model: str,
    system_prompt: str,
    client: ollama.Client,
) -> dict:
    user_msg = (
        f"The following is an LCL-encoded instruction. "
        f"Explain in plain English what it means: {scenario['lcl_input']}"
    )
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    llm_output = response.message.content.strip()

    return {
        "scenario_id": scenario["id"],
        "lcl_input": scenario["lcl_input"],
        "llm_output": llm_output,
        "expected_meaning": scenario["expected_english_meaning"],
    }


def run_compression_test(scenarios: list[dict]) -> dict:
    total_english_tokens = 0
    total_lcl_tokens = 0

    pairs = []
    for s in scenarios:
        if s["type"] == "comprehension":
            eng_tokens = count_tokens(s["expected_english_meaning"])
            lcl_tokens = count_tokens(s["lcl_input"])
            total_english_tokens += eng_tokens
            total_lcl_tokens += lcl_tokens
            pairs.append({
                "english": s["expected_english_meaning"],
                "lcl": s["lcl_input"],
                "english_tokens": eng_tokens,
                "lcl_tokens": lcl_tokens,
                "ratio": 1 - (lcl_tokens / eng_tokens) if eng_tokens > 0 else 0,
            })

    return {
        "pairs": pairs,
        "total_english_tokens": total_english_tokens,
        "total_lcl_tokens": total_lcl_tokens,
        "overall_compression_ratio": (
            1 - (total_lcl_tokens / total_english_tokens)
            if total_english_tokens > 0
            else 0
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 0 LCL experiments")
    parser.add_argument("--model", required=True, help="Ollama model name")
    parser.add_argument(
        "--host", default="http://localhost:11434", help="Ollama API host"
    )
    parser.add_argument(
        "--output", default="tests/phase0/raw_results.json", help="Output file"
    )
    args = parser.parse_args()

    client = ollama.Client(host=args.host)
    system_prompt = load_system_prompt()
    scenarios = load_scenarios()
    lexicon = load_lexicon(DATA_DIR / "phase0-lexicon.json")

    symbol_set = set(lexicon.symbol_to_entry().keys())
    marker_set = lexicon.marker_symbols()

    print(f"Running Phase 0 experiments with model: {args.model}")
    print(f"Lexicon: {len(lexicon.entries)} entries")
    print()

    results = {
        "model": args.model,
        "lexicon_version": lexicon.version,
        "production_tests": [],
        "comprehension_tests": [],
        "compression": None,
    }

    # Production tests
    prod_scenarios = [s for s in scenarios if s["type"] == "production"]
    print(f"--- Production Tests ({len(prod_scenarios)} scenarios) ---")
    for scenario in prod_scenarios:
        print(f"  {scenario['id']}: {scenario['english_instruction']}")
        result = run_production_test(scenario, args.model, system_prompt, client)
        print(f"    LLM output: {result['llm_output']}")

        # Score: what fraction of output chars are valid symbols?
        output_chars = [ch for ch in result["llm_output"] if not ch.isspace()]
        valid = sum(1 for ch in output_chars if ch in symbol_set or ch in marker_set)
        score = valid / len(output_chars) if output_chars else 0
        result["valid_symbol_ratio"] = score
        print(f"    Valid symbol ratio: {score:.2%}")
        results["production_tests"].append(result)

    print()

    # Comprehension tests
    comp_scenarios = [s for s in scenarios if s["type"] == "comprehension"]
    print(f"--- Comprehension Tests ({len(comp_scenarios)} scenarios) ---")
    for scenario in comp_scenarios:
        print(f"  {scenario['id']}: {scenario['lcl_input']}")
        result = run_comprehension_test(scenario, args.model, system_prompt, client)
        print(f"    LLM interpretation: {result['llm_output'][:100]}")
        results["comprehension_tests"].append(result)

    print()

    # Compression tests
    print("--- Compression Tests ---")
    compression = run_compression_test(scenarios)
    results["compression"] = compression
    for pair in compression["pairs"]:
        print(
            f"  '{pair['english'][:40]}...' → '{pair['lcl']}': "
            f"{pair['english_tokens']}→{pair['lcl_tokens']} tokens "
            f"({pair['ratio']:.0%} reduction)"
        )
    print(f"  Overall compression: {compression['overall_compression_ratio']:.0%}")

    # Measure system prompt token cost
    prompt_tokens = count_tokens(system_prompt)
    results["system_prompt_tokens"] = prompt_tokens
    print(f"\n  System prompt cost: {prompt_tokens} tokens")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
