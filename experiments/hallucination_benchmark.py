"""
Benchmark hallucination detection using sparse wiki grounding.

Usage:
    python -m experiments.hallucination_benchmark \
        --output reports/verification_baseline.json
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from wiki_grounding.verifier import ClaimVerifier, VerificationStatus
from wiki_grounding.store import EntityStore


def run_benchmark(claims: List[Dict]) -> Dict:
    """Run verification benchmark."""
    
    # Initialize verifier
    # Ensure build_demo_db.py has been run
    db_path = Path("data/wiki_grounding.db")
    if not db_path.exists():
        print("Database not found. Please run scripts/build_demo_db.py first.")
        # Attempt to run it? Or fail. The plan says it's pre-run.
        # Check if user needs it. For now, assume it might be there or will be.
        # But wait, previous conversation summary says "Prepared data by running scripts/build_demo_db.py".
        pass

    store = EntityStore(str(db_path))
    verifier = ClaimVerifier(store)

    results = []
    
    for item in claims:
        start = time.perf_counter()
        result = verifier.verify(item["claim"])
        latency = (time.perf_counter() - start) * 1000

        results.append({
            "claim": item["claim"],
            "truth": item["label"],
            "score": result.confidence,
            "verdict": result.status == VerificationStatus.SUPPORTED,
            "latency_ms": latency,
            "grounding": result.confidence,
        })

    # Compute metrics
    correct = sum(1 for r in results if r["verdict"] == r["truth"])
    accuracy = correct / len(results) if results else 0
    mean_latency = sum(r["latency_ms"] for r in results) / len(results) if results else 0

    return {
        "accuracy": accuracy,
        "mean_latency_ms": mean_latency,
        "n_claims": len(results),
        "results": results
    }


def load_benchmark_claims() -> List[Dict]:
    """Load or generate benchmark claims."""
    # Matches the semantic_probing benchmark for consistency
    true_claims = [
        "Paris is the capital of France.",
        "Water freezes at 0 degrees Celsius.",
        "Einstein developed the theory of relativity.",
    ]
    false_claims = [
        "Paris is the capital of Germany.",
        "Water freezes at 50 degrees Celsius.",
        "Einstein invented the telephone.",
    ]
    
    claims = []
    for c in true_claims:
        claims.append({"claim": c, "label": True})
    for c in false_claims:
        claims.append({"claim": c, "label": False})
        
    return claims


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/verification_baseline.json")
    args = parser.parse_args()

    claims = load_benchmark_claims()
    metrics = run_benchmark(claims)

    print(f"\n=== Verification Benchmark ===")
    print(f"Accuracy: {metrics['accuracy']:.1%}")
    print(f"Mean Latency: {metrics['mean_latency_ms']:.1f}ms")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
