#!/usr/bin/env python3
"""
LLM Hallucination Detection Benchmark

This demonstrates sparse wiki grounding for factual claim verification -
a key capability for AI safety research. We benchmark detection of
common LLM hallucination patterns.

Key Metrics for LLM Research:
- Precision: % of flagged claims that are actually false
- Recall: % of false claims that are detected
- Latency: Time per verification (real-time feasibility)
- Coverage: % of claims that can be grounded

Usage:
    PYTHONPATH=src python examples/hallucination_detection.py
"""

import time
from dataclasses import dataclass
from typing import List, Tuple
from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus


@dataclass
class BenchmarkClaim:
    """A claim with ground truth label for benchmarking."""
    text: str
    is_true: bool
    category: str  # geographic, attribution, property, temporal


# Benchmark dataset: categorized claims with ground truth
BENCHMARK_CLAIMS = [
    # === GEOGRAPHIC CLAIMS ===
    # True
    BenchmarkClaim("Paris is in France", True, "geographic"),
    BenchmarkClaim("The Eiffel Tower is in Paris", True, "geographic"),
    BenchmarkClaim("London is in England", True, "geographic"),
    BenchmarkClaim("The Statue of Liberty is in New York City", True, "geographic"),
    BenchmarkClaim("The Great Wall of China is in China", True, "geographic"),
    BenchmarkClaim("Rome is in Italy", True, "geographic"),
    BenchmarkClaim("Tokyo is in Japan", True, "geographic"),
    BenchmarkClaim("Berlin is in Germany", True, "geographic"),
    # False
    BenchmarkClaim("The Eiffel Tower is in London", False, "geographic"),
    BenchmarkClaim("Paris is in Germany", False, "geographic"),
    BenchmarkClaim("The Colosseum is in Paris", False, "geographic"),
    BenchmarkClaim("Tokyo is in China", False, "geographic"),

    # === ATTRIBUTION CLAIMS ===
    # True
    BenchmarkClaim("Albert Einstein created the theory of relativity", True, "attribution"),
    BenchmarkClaim("Marie Curie discovered radioactivity", True, "attribution"),
    BenchmarkClaim("Marie Curie discovered polonium", True, "attribution"),
    BenchmarkClaim("Marie Curie discovered radium", True, "attribution"),
    BenchmarkClaim("Shakespeare wrote Hamlet", True, "attribution"),
    BenchmarkClaim("Thomas Edison invented the light bulb", True, "attribution"),
    BenchmarkClaim("Alexander Graham Bell invented the telephone", True, "attribution"),
    BenchmarkClaim("Isaac Newton discovered gravity", True, "attribution"),
    BenchmarkClaim("Charles Darwin developed evolution", True, "attribution"),
    # False (entity swap hallucinations - very common in LLMs)
    BenchmarkClaim("Thomas Edison invented the telephone", False, "attribution"),
    BenchmarkClaim("Alexander Graham Bell invented the light bulb", False, "attribution"),
    BenchmarkClaim("Albert Einstein invented the light bulb", False, "attribution"),
    BenchmarkClaim("Einstein discovered radioactivity", False, "attribution"),

    # === PROPERTY CLAIMS ===
    # True
    BenchmarkClaim("Paris is the capital of France", True, "property"),
    BenchmarkClaim("London is the capital of United Kingdom", True, "property"),
    BenchmarkClaim("Berlin is the capital of Germany", True, "property"),
    BenchmarkClaim("Rome is the capital of Italy", True, "property"),
    BenchmarkClaim("Tokyo is the capital of Japan", True, "property"),
    # False
    BenchmarkClaim("Berlin is the capital of France", False, "property"),
    BenchmarkClaim("Paris is the capital of Italy", False, "property"),

    # === RELATION CLAIMS ===
    # True
    BenchmarkClaim("Marie Curie is a spouse of Pierre Curie", True, "relation"),
    # False
    BenchmarkClaim("Einstein is a spouse of Marie Curie", False, "relation"),
]


def run_benchmark():
    """Run full hallucination detection benchmark."""
    print("=" * 70)
    print("LLM HALLUCINATION DETECTION BENCHMARK")
    print("Sparse Wiki Grounding for Factual Verification")
    print("=" * 70)
    print()

    # Initialize
    store = EntityStore("data/entities_demo.db")
    verifier = ClaimVerifier(store)

    entity_count = store.count()
    relation_count = store.conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    print(f"Knowledge Base: {entity_count:,} entities, {relation_count:,} relations")
    print(f"Benchmark Size: {len(BENCHMARK_CLAIMS)} claims")
    print()

    # Run verification
    results: List[Tuple[BenchmarkClaim, VerificationStatus, float, float]] = []
    total_time = 0

    for claim in BENCHMARK_CLAIMS:
        start = time.perf_counter()
        result = verifier.verify(claim.text)
        elapsed = (time.perf_counter() - start) * 1000
        total_time += elapsed
        results.append((claim, result.status, result.confidence, elapsed))

    # Calculate metrics
    print("-" * 70)
    print("DETAILED RESULTS")
    print("-" * 70)

    # Track metrics
    tp, tn, fp, fn = 0, 0, 0, 0
    verified, contradicted, unverifiable = 0, 0, 0

    by_category = {}

    for claim, status, confidence, elapsed in results:
        # Categorize result
        if status == VerificationStatus.SUPPORTED:
            verified += 1
            if claim.is_true:
                tp += 1
                marker = "\033[92m[TP]\033[0m"
            else:
                fp += 1  # We said true but it was false
                marker = "\033[91m[FP]\033[0m"
        elif status == VerificationStatus.CONTRADICTED:
            contradicted += 1
            if not claim.is_true:
                tn += 1
                marker = "\033[92m[TN]\033[0m"
            else:
                fn += 1  # We said false but it was true
                marker = "\033[91m[FN]\033[0m"
        else:
            unverifiable += 1
            marker = "\033[93m[??]\033[0m"

        # Track by category
        cat = claim.category
        if cat not in by_category:
            by_category[cat] = {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "unk": 0}
        if status == VerificationStatus.SUPPORTED:
            if claim.is_true:
                by_category[cat]["tp"] += 1
            else:
                by_category[cat]["fp"] += 1
        elif status == VerificationStatus.CONTRADICTED:
            if not claim.is_true:
                by_category[cat]["tn"] += 1
            else:
                by_category[cat]["fn"] += 1
        else:
            by_category[cat]["unk"] += 1

        # Print result
        truth = "TRUE" if claim.is_true else "FALSE"
        print(f"{marker} [{claim.category:12}] ({truth:5}) {claim.text[:50]:50} [{elapsed:.1f}ms]")

    # Summary metrics
    print()
    print("=" * 70)
    print("BENCHMARK METRICS")
    print("=" * 70)

    total_decisions = tp + tn + fp + fn
    accuracy = (tp + tn) / total_decisions if total_decisions > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # False detection metrics (for hallucination detection, we care about catching FALSE claims)
    false_precision = tn / (tn + fn) if (tn + fn) > 0 else 0
    false_recall = tn / (tn + fp) if (tn + fp) > 0 else 0

    coverage = total_decisions / len(BENCHMARK_CLAIMS)

    print(f"\n{'Overall Metrics':30}")
    print(f"  {'Accuracy:':<20} {accuracy:.1%}")
    print(f"  {'Coverage:':<20} {coverage:.1%}")
    print(f"  {'Avg Latency:':<20} {total_time/len(BENCHMARK_CLAIMS):.2f}ms")
    print(f"  {'Total Time:':<20} {total_time:.1f}ms")

    print(f"\n{'True Claim Detection':30}")
    print(f"  {'Precision:':<20} {precision:.1%}")
    print(f"  {'Recall:':<20} {recall:.1%}")
    print(f"  {'F1 Score:':<20} {f1:.1%}")

    print(f"\n{'Hallucination Detection':30} (detecting FALSE claims)")
    print(f"  {'Precision:':<20} {false_precision:.1%}")
    print(f"  {'Recall:':<20} {false_recall:.1%}")

    # Per-category breakdown
    print(f"\n{'By Category':30}")
    for cat, metrics in sorted(by_category.items()):
        cat_total = sum(metrics.values()) - metrics["unk"]
        cat_correct = metrics["tp"] + metrics["tn"]
        cat_acc = cat_correct / cat_total if cat_total > 0 else 0
        print(f"  {cat:15} accuracy={cat_acc:.1%} (TP={metrics['tp']}, TN={metrics['tn']}, FP={metrics['fp']}, FN={metrics['fn']}, ?={metrics['unk']})")

    # Confusion matrix
    print(f"\n{'Confusion Matrix':30}")
    print(f"                    Predicted")
    print(f"                    TRUE    FALSE   UNK")
    print(f"  Actual TRUE       {tp:4}    {fn:4}    {sum(1 for c, s, _, _ in results if c.is_true and s not in [VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED]):4}")
    print(f"  Actual FALSE      {fp:4}    {tn:4}    {sum(1 for c, s, _, _ in results if not c.is_true and s not in [VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED]):4}")

    # LLM Research implications
    print()
    print("=" * 70)
    print("IMPLICATIONS FOR LLM SAFETY")
    print("=" * 70)
    print(f"""
This benchmark demonstrates key capabilities for LLM hallucination detection:

1. REAL-TIME FEASIBILITY
   - {total_time/len(BENCHMARK_CLAIMS):.2f}ms average per claim enables real-time verification
   - Can verify ~{1000/(total_time/len(BENCHMARK_CLAIMS)):.0f} claims/second

2. ENTITY SWAP DETECTION
   - Common LLM failure mode: swapping related entities
   - Example: "Edison invented the telephone" (actually Bell)
   - Grounding enables automatic correction

3. GEOGRAPHIC GROUNDING
   - Hierarchical SPATIAL dimension catches location errors
   - Example: "Eiffel Tower is in London" -> detected via Paris path

4. TRANSPARENT CORRECTIONS
   - Not just detection: provides correct information
   - Enables automatic fact-checking pipelines

5. COVERAGE-ACCURACY TRADEOFF
   - {coverage:.1%} of claims can be verified ({unverifiable} unverifiable)
   - {accuracy:.1%} accuracy on verifiable claims
   - Unverifiable claims can be flagged for human review
""")


if __name__ == "__main__":
    run_benchmark()
