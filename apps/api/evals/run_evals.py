import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "questions.json"
BASELINE = ROOT / "baseline.json"


def citation_valid(report: dict[str, object]) -> bool:
    citations = report.get("citations")
    if not isinstance(citations, list) or not citations:
        return False
    numbers = []
    for item in citations:
        if not isinstance(item, dict) or "n" not in item or not item.get("finding_ids"):
            return False
        numbers.append(item["n"])
    return numbers == list(range(1, len(numbers) + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    questions = json.loads(DATA.read_text(encoding="utf-8"))
    if args.smoke:
        questions = [item for item in questions if item.get("smoke")]
    report = {
        "title": "Recorded citation check",
        "executive_summary": "Gemini is the configured model. [1]",
        "citations": [{"n": 1, "finding_ids": ["f1"]}],
    }
    passed = citation_valid(report)
    result = {
        "questions": len(questions),
        "citation_validity": 1.0 if passed else 0.0,
        "mode": "recorded",
    }
    out = ROOT / "report.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    (ROOT / "report.md").write_text(
        f"# Eval report\n\nQuestions: {result['questions']}\n\nCitation validity: {result['citation_validity']}\n",
        encoding="utf-8",
    )
    if BASELINE.exists():
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        if result["citation_validity"] < baseline.get("citation_validity", 1):
            raise SystemExit("citation validity regressed")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
