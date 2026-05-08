"""Analyze test_runner log to categorize failures for the latest completed run."""

import re
import sys
from collections import Counter, defaultdict
from typing import Any, Optional

LOG_FILE = "output/test_run.log"

P_CASE_START = re.compile(r"Start testing case: (.+)")
P_PARSE_FAIL = re.compile(r"解析失败，原始输出: (.+)")
P_VALIDATE_RETRY = re.compile(r"校验需重试: (.+)")
P_TYPE_REJECT = re.compile(r"TYPE rejected: (.+)")
P_COMPLETE_REJECT = re.compile(r"COMPLETE rejected: (.+)")
P_CHECKER_MISMATCH = re.compile(r"\[Checker\] Action mismatch: expect \[(\w+)\], got \[(\w+)\]")
P_CHECKER_CLICK_FAIL = re.compile(r"\[Checker\] CLICK failed: (.+)")
P_CHECKER_TYPE_FAIL = re.compile(r"\[Checker\] TYPE: (.+)")
P_CHECKER_OPEN_FAIL = re.compile(r"\[Checker\] OPEN: (.+)")
P_SCORE = re.compile(r"\[No\. \d+: (.+?)\] Score: (\d+)/(\d+) = ([0-9.]+)")
P_STUCK = re.compile(r"检测到重复点击")
P_FALLBACK = re.compile(r"API调用失败|提取模型输出失败")
P_STEP_ACCURACY = re.compile(r"Step Level Accuracy: ([0-9.]+)")
P_CASE_ACCURACY = re.compile(r"Case Level Accuracy: ([0-9.]+)")
P_ACTION_POLICY_DECISION = re.compile(r"ACTION_POLICY decision changed=True .* reason=(\S+) confidence=(\S+)")
P_ACTION_POLICY_ACCEPTED = re.compile(r"ACTION_POLICY accepted .* reason=(\S+)")
P_ACTION_POLICY_REJECTED = re.compile(r"ACTION_POLICY rejected .* reason=(\S+) confidence=(\S+) retry_reason=(.+)")


def _new_report() -> dict[str, Any]:
    return {
        "step_accuracy": None,
        "case_accuracy": None,
        "case_scores": {},
        "case_failures": defaultdict(list),
        "category_counts": Counter(),
        "parse_fail_examples": [],
        "action_policy": {
            "corrected_steps": 0,
            "accepted_corrections": 0,
            "rejected_corrections": 0,
            "rejected_correction_cases": [],
            "reasons": {},
        },
    }


def _record_case_failure(report: dict[str, Any], current_case: str, reason: str, category: str) -> None:
    report["case_failures"][current_case].append(reason)
    report["category_counts"][category] += 1


def _finalize_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_accuracy": report["step_accuracy"],
        "case_accuracy": report["case_accuracy"],
        "case_scores": dict(report["case_scores"]),
        "case_failures": {case: reasons[:] for case, reasons in report["case_failures"].items()},
        "category_counts": dict(report["category_counts"]),
        "parse_fail_examples": list(report["parse_fail_examples"]),
        "action_policy": dict(report["action_policy"]),
    }


def analyze_text(log_text: str) -> dict[str, Any]:
    latest_completed_report: Optional[dict[str, Any]] = None
    current_report = _new_report()
    current_case = ""

    for line in log_text.splitlines():
        step_accuracy_match = P_STEP_ACCURACY.search(line)
        if step_accuracy_match:
            current_report["step_accuracy"] = float(step_accuracy_match.group(1))
            continue

        case_accuracy_match = P_CASE_ACCURACY.search(line)
        if case_accuracy_match:
            current_report["case_accuracy"] = float(case_accuracy_match.group(1))
            latest_completed_report = _finalize_report(current_report)
            current_report = _new_report()
            current_case = ""
            continue

        case_start_match = P_CASE_START.search(line)
        if case_start_match:
            current_case = case_start_match.group(1)
            continue

        score_match = P_SCORE.search(line)
        if score_match:
            case_name, earned, total, ratio = score_match.groups()
            current_report["case_scores"][case_name] = {
                "earned": int(earned),
                "total": int(total),
                "ratio": float(ratio),
            }
            continue

        parse_fail_match = P_PARSE_FAIL.search(line)
        if parse_fail_match:
            raw = parse_fail_match.group(1).strip()[:120]
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"Parser failed: {raw}",
                category="Parser failed",
            )
            if len(current_report["parse_fail_examples"]) < 20:
                current_report["parse_fail_examples"].append(f"  [{current_case}] {raw}")
            continue

        validate_retry_match = P_VALIDATE_RETRY.search(line)
        if validate_retry_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"Validator retry: {validate_retry_match.group(1).strip()}",
                category="Validator retry",
            )
            continue

        type_reject_match = P_TYPE_REJECT.search(line)
        if type_reject_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"TYPE rejected: {type_reject_match.group(1)}",
                category="TYPE rejected",
            )
            continue

        complete_reject_match = P_COMPLETE_REJECT.search(line)
        if complete_reject_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"COMPLETE rejected: {complete_reject_match.group(1)}",
                category="COMPLETE rejected",
            )
            continue

        mismatch_match = P_CHECKER_MISMATCH.search(line)
        if mismatch_match:
            expected, got = mismatch_match.group(1), mismatch_match.group(2)
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"Action mismatch: expect={expected}, got={got}",
                category=f"expect {expected}, got {got}",
            )
            continue

        click_fail_match = P_CHECKER_CLICK_FAIL.search(line)
        if click_fail_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"CLICK failed: {click_fail_match.group(1).strip()[:80]}",
                category="CLICK failed",
            )
            continue

        type_fail_match = P_CHECKER_TYPE_FAIL.search(line)
        if type_fail_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"TYPE mismatch: {type_fail_match.group(1).strip()[:80]}",
                category="TYPE mismatch",
            )
            continue

        open_fail_match = P_CHECKER_OPEN_FAIL.search(line)
        if open_fail_match:
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason=f"OPEN mismatch: {open_fail_match.group(1).strip()[:80]}",
                category="OPEN mismatch",
            )
            continue

        if P_STUCK.search(line):
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason="Stuck (repeated clicks)",
                category="Stuck (repeated clicks)",
            )
            continue

        action_policy_decision_match = P_ACTION_POLICY_DECISION.search(line)
        if action_policy_decision_match:
            reason, _confidence = action_policy_decision_match.groups()
            current_report["action_policy"]["corrected_steps"] += 1
            current_report["action_policy"]["reasons"][reason] = (
                current_report["action_policy"]["reasons"].get(reason, 0) + 1
            )
            continue

        action_policy_accepted_match = P_ACTION_POLICY_ACCEPTED.search(line)
        if action_policy_accepted_match:
            current_report["action_policy"]["accepted_corrections"] += 1
            continue

        action_policy_rejected_match = P_ACTION_POLICY_REJECTED.search(line)
        if action_policy_rejected_match:
            current_report["action_policy"]["rejected_corrections"] += 1
            if current_case and current_case not in current_report["action_policy"]["rejected_correction_cases"]:
                current_report["action_policy"]["rejected_correction_cases"].append(current_case)
            continue

        if P_FALLBACK.search(line):
            _record_case_failure(
                report=current_report,
                current_case=current_case,
                reason="Fallback triggered",
                category="Fallback triggered",
            )

    if latest_completed_report is None:
        latest_completed_report = _finalize_report(current_report)

    return latest_completed_report


def _print_report(report: dict[str, Any]) -> None:
    print("=" * 60)
    print("Latest Completed Run Summary")
    print("=" * 60)
    print(f"  Step Level Accuracy: {report['step_accuracy']}")
    print(f"  Case Level Accuracy: {report['case_accuracy']}")
    print()

    if report["case_scores"]:
        print("Per-Case Scores")
        print("-" * 60)
        for case_name, score in report["case_scores"].items():
            print(f"  {case_name}: {score['earned']}/{score['total']} = {score['ratio']:.2f}")
        print()

    print("Failure Category Summary")
    print("-" * 60)
    for category, count in sorted(report["category_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {category}: {count}")
    print()

    print("Action Policy Observability")
    print("-" * 60)
    print(f"  corrected_steps: {report['action_policy']['corrected_steps']}")
    print(f"  accepted_corrections: {report['action_policy']['accepted_corrections']}")
    print(f"  rejected_corrections: {report['action_policy']['rejected_corrections']}")
    print(f"  rejected_correction_cases: {report['action_policy']['rejected_correction_cases']}")
    print(f"  reasons: {report['action_policy']['reasons']}")
    print()

    if report["parse_fail_examples"]:
        print("Parser Failure Examples")
        print("-" * 60)
        for example in report["parse_fail_examples"]:
            print(example)
        print()

    if report["case_failures"]:
        print("Per-Case Failure Details")
        print("-" * 60)
        for case_name, reasons in sorted(report["case_failures"].items()):
            print(f"\n  [{case_name}]")
            for reason in reasons:
                print(f"    - {reason}")

    print(f"\nTotal cases with failures: {len(report['case_failures'])}")
    print(f"Total failure events: {sum(report['category_counts'].values())}")


def analyze(log_path: str) -> dict[str, Any]:
    with open(log_path, "r", encoding="utf-8") as file:
        report = analyze_text(file.read())
    _print_report(report)
    return report


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else LOG_FILE
    analyze(path)
