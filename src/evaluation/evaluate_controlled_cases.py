import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "ground_truth.csv"

FINDINGS_PATH = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "evaluation_findings.json"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def evaluate_controlled_cases():

    with GROUND_TRUTH_PATH.open(
        "r", encoding="utf-8", newline=""
    ) as file:
        ground_truth = list(csv.DictReader(file))

    with FINDINGS_PATH.open(
        "r", encoding="utf-8"
    ) as file:
        findings = json.load(file)

    true_positives = 0
    false_negatives = 0
    results = []

    matched_finding_indexes = set()

    for case in ground_truth:

        matched = False

        for index, finding in enumerate(findings):

            if (
                finding["rule_id"] == case["rule_id"]
                and finding["entity_type"] == case["entity_type"]
                and finding["entity_id"] == case["entity_id"]
            ):
                matched = True
                matched_finding_indexes.add(index)
                break

        if matched:
            true_positives += 1
            status = "PASS"
        else:
            false_negatives += 1
            status = "FAIL"

        results.append({
            "case_id": case["case_id"],
            "rule_id": case["rule_id"],
            "entity_id": case["entity_id"],
            "expected": case["expected_result"],
            "actual": "DETECT" if matched else "NOT_DETECTED",
            "status": status,
        })

    total_cases = len(ground_truth)

    detection_rate = (
        true_positives / total_cases
        if total_cases else 0
    )

    # Precision and F1 are intentionally not calculated:
    # the complete set of positive and negative labels
    # is not available yet.

    summary = {
        "evaluation_type": "controlled_anomaly_scenarios",
        "total_cases": total_cases,
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "false_positives": None,
        "precision": None,
        "recall": detection_rate,
        "f1_score": None,
        "detection_rate": detection_rate,
        "precision_note": (
            "Not calculated: complete negative ground truth "
            "is not available."
        ),
        "f1_note": (
            "Not calculated because precision is unavailable."
        ),
        "unmatched_findings_excluded_from_metrics": (
            len(findings) - len(matched_finding_indexes)
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = (
        OUTPUT_DIR / "controlled_evaluation_summary.json"
    )

    results_path = (
        OUTPUT_DIR / "controlled_evaluation_by_case.csv"
    )

    summary_path.write_text(
        json.dumps(summary, indent=4),
        encoding="utf-8",
    )

    with results_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id",
                "rule_id",
                "entity_id",
                "expected",
                "actual",
                "status",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n--- CONTROLLED EVALUATION SUMMARY ---")
    print(f"Total cases: {total_cases}")
    print(f"True positives: {true_positives}")
    print(f"False negatives: {false_negatives}")
    print(f"Detection rate: {detection_rate:.2%}")
    print("Precision: Not calculated")
    print("F1 score: Not calculated")

    print(f"\nSummary saved: {summary_path}")
    print(f"Case results saved: {results_path}")


if __name__ == "__main__":
    evaluate_controlled_cases()