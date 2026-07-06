"""
IngreLens AI — evaluation harness.

Run:
    python -m evaluation.run_evaluation
    python -m evaluation.run_evaluation --report evaluation/last_report.md

Runs the real CoordinatorAgent and real service classes (no mocks) against
the three JSON datasets in evaluation/datasets/, and reports four numbers a
judge can check against the raw case list:

  - routing accuracy %      — did CoordinatorAgent.handle() call the agents
                               the case says it should (its agents_used trail)?
  - classification accuracy % — did the diet-category outcome match what the
                               case expects?
  - fallback success rate %  — for the cases designed to be broken (garbage
                               barcodes, empty ingredients, noisy OCR text),
                               did the system degrade gracefully instead of
                               crashing or silently returning nothing?
  - tool execution success % — across every case in every dataset, did the
                               underlying service call complete without
                               raising an exception at all?
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.llm_service import IngredientAnalystAgent
from backend.services.coordinator_agent import CoordinatorAgent

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


@dataclass
class CaseResult:
    dataset: str
    case_id: str
    passed: bool
    routing_checked: bool = False
    routing_ok: bool = False
    classification_checked: bool = False
    classification_ok: bool = False
    fallback_checked: bool = False
    fallback_ok: bool = False
    tool_execution_ok: bool = True
    detail: str = ""


def _build_coordinator() -> CoordinatorAgent:
    return CoordinatorAgent(
        product_service=ProductFetchService(),
        ocr_service=OCRService(),
        analysis_service=IngredientAnalysisService(),
        analyst_agent=IngredientAnalystAgent(),
    )


def run_food_label_cases(coordinator: CoordinatorAgent) -> list[CaseResult]:
    cases = json.loads((DATASETS_DIR / "food_label_edge_cases.json").read_text())
    results = []
    for case in cases:
        cid = case["id"]
        try:
            if case["case_type"] == "multi_product_comparison":
                a = coordinator.handle(
                    ingredients_text=case["input"]["product_a"]["ingredients_text"],
                    product_name=case["input"]["product_a"]["product_name"],
                )
                b = coordinator.handle(
                    ingredients_text=case["input"]["product_b"]["ingredients_text"],
                    product_name=case["input"]["product_b"]["product_name"],
                )
                score_a = a.analysis.health_score if a.analysis else -1
                score_b = b.analysis.health_score if b.analysis else -1
                ok = score_a > score_b
                results.append(CaseResult(
                    "food_label_edge_cases", cid, passed=ok,
                    classification_checked=True, classification_ok=ok,
                    detail=f"health_score A={score_a} B={score_b}",
                ))
                continue

            res = coordinator.handle(
                ingredients_text=case["input"].get("ingredients_text"),
                product_name=case["input"].get("product_name", ""),
            )

            routing_ok = True
            routing_checked = "expected_agents_used" in case
            if routing_checked:
                routing_ok = res.agents_used == case["expected_agents_used"]

            classification_ok = True
            classification_checked = False
            if "expect_error_result" in case:
                classification_checked = True
                classification_ok = res.kind == "error"
            elif "expected_diet_category_in" in case:
                classification_checked = True
                classification_ok = (
                    res.analysis is not None
                    and res.analysis.overall_vegan in case["expected_diet_category_in"]
                )
            if "expect_not" in case and res.analysis is not None:
                classification_checked = True
                classification_ok = classification_ok and (res.analysis.overall_vegan != case["expect_not"])

            passed = routing_ok and classification_ok
            results.append(CaseResult(
                "food_label_edge_cases", cid, passed=passed,
                routing_checked=routing_checked, routing_ok=routing_ok,
                classification_checked=classification_checked, classification_ok=classification_ok,
                detail=f"kind={res.kind} agents_used={res.agents_used}",
            ))
        except Exception as e:
            results.append(CaseResult(
                "food_label_edge_cases", cid, passed=False,
                tool_execution_ok=False, detail=f"CRASHED: {e}",
            ))
    return results


def run_allergy_cases(analysis_service: IngredientAnalysisService) -> list[CaseResult]:
    cases = json.loads((DATASETS_DIR / "allergy_cases.json").read_text())
    results = []
    for case in cases:
        cid = case["id"]
        try:
            r = analysis_service.analyze(
                case["input"]["ingredients_text"], case["input"]["product_name"]
            )
            expected = set(case["expected_allergens_include"])
            found = set(r.allergens_detected)
            ok = expected.issubset(found)
            results.append(CaseResult(
                "allergy_cases", cid, passed=ok,
                classification_checked=True, classification_ok=ok,
                detail=f"expected>={sorted(expected)} found={sorted(found)}",
            ))
        except Exception as e:
            results.append(CaseResult(
                "allergy_cases", cid, passed=False,
                tool_execution_ok=False, detail=f"CRASHED: {e}",
            ))
    return results


def run_barcode_fail_cases(coordinator: CoordinatorAgent) -> list[CaseResult]:
    cases = json.loads((DATASETS_DIR / "barcode_fail_cases.json").read_text())
    results = []
    for case in cases:
        cid = case["id"]
        try:
            res = coordinator.handle(barcode=case["barcode"] or None)

            fallback_checked = False
            fallback_ok = True
            if case.get("expect_coordinator_error"):
                fallback_checked = True
                fallback_ok = res.kind == "error"
            elif case.get("expect_fallback") is True:
                fallback_checked = True
                fallback_ok = res.kind == "analysis" and res.product_name is not None
            elif case.get("expect_fallback") is False:
                fallback_checked = True
                # A real known barcode shouldn't route through the "no barcode" error path.
                fallback_ok = res.kind == "analysis"

            routing_checked = True
            routing_ok = ("product_fetch" in res.agents_used) or (res.kind == "error" and not case["barcode"])

            passed = fallback_ok and routing_ok
            results.append(CaseResult(
                "barcode_fail_cases", cid, passed=passed,
                routing_checked=routing_checked, routing_ok=routing_ok,
                fallback_checked=fallback_checked, fallback_ok=fallback_ok,
                detail=f"kind={res.kind} agents_used={res.agents_used}",
            ))
        except Exception as e:
            results.append(CaseResult(
                "barcode_fail_cases", cid, passed=False,
                tool_execution_ok=False, detail=f"CRASHED: {e}",
            ))
    return results


def compute_metrics(all_results: list[CaseResult]) -> dict:
    def pct(n, d):
        return round(100.0 * n / d, 1) if d else None

    routing_checked = [r for r in all_results if r.routing_checked]
    classification_checked = [r for r in all_results if r.classification_checked]
    fallback_checked = [r for r in all_results if r.fallback_checked]

    return {
        "total_cases": len(all_results),
        "overall_pass_rate_pct": pct(sum(r.passed for r in all_results), len(all_results)),
        "routing_accuracy_pct": pct(sum(r.routing_ok for r in routing_checked), len(routing_checked)),
        "routing_cases_checked": len(routing_checked),
        "classification_accuracy_pct": pct(sum(r.classification_ok for r in classification_checked), len(classification_checked)),
        "classification_cases_checked": len(classification_checked),
        "fallback_success_rate_pct": pct(sum(r.fallback_ok for r in fallback_checked), len(fallback_checked)),
        "fallback_cases_checked": len(fallback_checked),
        "tool_execution_success_pct": pct(sum(r.tool_execution_ok for r in all_results), len(all_results)),
    }


def render_report(all_results: list[CaseResult], metrics: dict) -> str:
    lines = [
        "# IngreLens AI — Evaluation Report",
        "",
        f"Total cases: **{metrics['total_cases']}** · Overall pass rate: **{metrics['overall_pass_rate_pct']}%**",
        "",
        "| Metric | Value | Cases checked |",
        "|---|---|---|",
        f"| Routing accuracy | {metrics['routing_accuracy_pct']}% | {metrics['routing_cases_checked']} |",
        f"| Classification accuracy | {metrics['classification_accuracy_pct']}% | {metrics['classification_cases_checked']} |",
        f"| Fallback success rate | {metrics['fallback_success_rate_pct']}% | {metrics['fallback_cases_checked']} |",
        f"| Tool execution success | {metrics['tool_execution_success_pct']}% | {metrics['total_cases']} |",
        "",
        "## Case-by-case detail",
        "",
        "| Dataset | Case | Result | Detail |",
        "|---|---|---|---|",
    ]
    for r in all_results:
        mark = "✅" if r.passed else "❌"
        lines.append(f"| {r.dataset} | {r.case_id} | {mark} | {r.detail} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="IngreLens AI evaluation harness")
    parser.add_argument("--report", type=str, default=None, help="Write a markdown report to this path")
    args = parser.parse_args()

    print("Building services + Coordinator (real classes, no mocks)...")
    t0 = time.time()
    analysis_service = IngredientAnalysisService()
    coordinator = CoordinatorAgent(
        product_service=ProductFetchService(),
        ocr_service=OCRService(),
        analysis_service=analysis_service,
        analyst_agent=IngredientAnalystAgent(),
    )
    print(f"  ready in {time.time() - t0:.1f}s\n")

    all_results: list[CaseResult] = []
    all_results += run_food_label_cases(coordinator)
    all_results += run_allergy_cases(analysis_service)
    all_results += run_barcode_fail_cases(coordinator)

    metrics = compute_metrics(all_results)

    print(f"{'Dataset':<24} {'Case':<45} {'Result':<8} Detail")
    print("-" * 110)
    for r in all_results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"{r.dataset:<24} {r.case_id:<45} {mark:<8} {r.detail}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    if args.report:
        report_path = Path(args.report)
        report_path.write_text(render_report(all_results, metrics))
        print(f"\nMarkdown report written to {report_path}")

    failed = [r for r in all_results if not r.passed]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
