#!/usr/bin/env python3
"""
Hallucination Detection Demo

This demonstrates how sparse wiki grounding can detect
factual hallucinations in LLM outputs - a key AI safety application.
"""

from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus

def demo_hallucination_detection():
    """
    Simulate checking LLM outputs for factual accuracy.

    In a real system, this would:
    1. Parse LLM output into claims
    2. Verify each claim against grounded knowledge
    3. Flag contradictions for human review
    """
    store = EntityStore("data/entities_demo.db")
    verifier = ClaimVerifier(store)

    # Simulated LLM outputs with some hallucinations
    llm_outputs = [
        # Correct claims
        "Marie Curie discovered radioactivity.",
        "The Great Wall of China is in China.",
        "Shakespeare wrote Hamlet.",

        # Hallucinations (incorrect)
        "Thomas Edison invented the telephone.",  # Bell did
        "The Statue of Liberty is in Paris.",     # It's in NYC
        "Einstein invented the light bulb.",      # Edison did

        # Plausible but unverifiable
        "Napoleon liked coffee.",
        "Cleopatra spoke seven languages.",
    ]

    print("=" * 60)
    print("HALLUCINATION DETECTION DEMO")
    print("=" * 60)
    print()

    results = {
        VerificationStatus.SUPPORTED: [],
        VerificationStatus.CONTRADICTED: [],
        VerificationStatus.UNVERIFIABLE: [],
        VerificationStatus.PLAUSIBLE: [],
    }

    for output in llm_outputs:
        result = verifier.verify(output)
        results[result.status].append(result)

        # Print with color coding
        if result.status == VerificationStatus.SUPPORTED:
            print(f"✓ VERIFIED: {output}")
            if result.supporting_evidence:
                print(f"  Evidence: {result.supporting_evidence[0]}")
        elif result.status == VerificationStatus.CONTRADICTED:
            print(f"✗ HALLUCINATION: {output}")
            print(f"  Correction: {result.correction}")
        elif result.status == VerificationStatus.PLAUSIBLE:
            print(f"~ PLAUSIBLE: {output}")
        else:
            print(f"? UNVERIFIABLE: {output}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Verified:     {len(results[VerificationStatus.SUPPORTED])}")
    print(f"  Hallucinations: {len(results[VerificationStatus.CONTRADICTED])}")
    print(f"  Plausible:    {len(results[VerificationStatus.PLAUSIBLE])}")
    print(f"  Unverifiable: {len(results[VerificationStatus.UNVERIFIABLE])}")
    print()
    print("Hallucination detection rate: {:.0%}".format(
        len(results[VerificationStatus.CONTRADICTED]) /
        (len(results[VerificationStatus.CONTRADICTED]) + len(results[VerificationStatus.SUPPORTED]))
        if results[VerificationStatus.CONTRADICTED] else 0
    ))


if __name__ == "__main__":
    demo_hallucination_detection()
