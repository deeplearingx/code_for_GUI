"""Analyze test_runner log to categorize failure reasons."""

import re
import sys
from collections import Counter, defaultdict

LOG_FILE = "output/test_run.log"

# Patterns
P_CASE_START = re.compile(r"Start testing case: (.+)")
P_STEP = re.compile(r"--- Step (\d+): Current Status (.+) ---")
P_PARSE_FAIL = re.compile(r"解析失败，原始输出: (.+)")
P_ACTION_OUT = re.compile(r"Agent Output: action=(\w+), params=(.+)")
P_VALIDATE_RETRY = re.compile(r"校验需重试: (.+)")
P_TYPE_REJECT = re.compile(r"TYPE rejected: (.+)")
P_COMPLETE_REJECT = re.compile(r"COMPLETE rejected: (.+)")
P_CHECKER_MISMATCH = re.compile(r"\[Checker\] Action mismatch: expect \[(\w+)\], got \[(\w+)\]")
P_CHECKER_CLICK_FAIL = re.compile(r"\[Checker\] CLICK failed: (.+)")
P_CHECKER_TYPE_FAIL = re.compile(r"\[Checker\] TYPE: (.+)")
P_CHECKER_OPEN_FAIL = re.compile(r"\[Checker\] OPEN: (.+)")
P_SCORE = re.compile(r"Score: (\d+)/(\d+)")
P_STUCK = re.compile(r"检测到重复点击")
P_FALLBACK = re.compile(r"API调用失败|提取模型输出失败")


def analyze(log_path: str) -> None:
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_case = ""
    case_failures: dict[str, list[str]] = defaultdict(list)
    category_counts: Counter = Counter()
    parse_fail_examples: list[str] = []

    for line in lines:
        m = P_CASE_START.search(line)
        if m:
            current_case = m.group(1)
            continue

        m = P_PARSE_FAIL.search(line)
        if m:
            raw = m.group(1).strip()[:120]
            reason = f"Parser failed: {raw}"
            case_failures[current_case].append(reason)
            category_counts["Parser failed"] += 1
            if len(parse_fail_examples) < 20:
                parse_fail_examples.append(f"  [{current_case}] {raw}")
            continue

        m = P_VALIDATE_RETRY.search(line)
        if m:
            reason = f"Validator retry: {m.group(1).strip()}"
            case_failures[current_case].append(reason)
            category_counts["Validator retry"] += 1
            continue

        m = P_TYPE_REJECT.search(line)
        if m:
            case_failures[current_case].append(f"TYPE rejected: {m.group(1)}")
            category_counts["TYPE rejected"] += 1
            continue

        m = P_COMPLETE_REJECT.search(line)
        if m:
            case_failures[current_case].append(f"COMPLETE rejected: {m.group(1)}")
            category_counts["COMPLETE rejected"] += 1
            continue

        m = P_CHECKER_MISMATCH.search(line)
        if m:
            expected, got = m.group(1), m.group(2)
            case_failures[current_case].append(f"Action mismatch: expect={expected}, got={got}")
            category_counts[f"Action mismatch ({expected}->{got})"] += 1
            continue

        m = P_CHECKER_CLICK_FAIL.search(line)
        if m:
            case_failures[current_case].append(f"CLICK out of range: {m.group(1).strip()[:80]}")
            category_counts["CLICK out of range"] += 1
            continue

        m = P_CHECKER_TYPE_FAIL.search(line)
        if m:
            case_failures[current_case].append(f"TYPE mismatch: {m.group(1).strip()[:80]}")
            category_counts["TYPE mismatch"] += 1
            continue

        m = P_CHECKER_OPEN_FAIL.search(line)
        if m:
            case_failures[current_case].append(f"OPEN mismatch: {m.group(1).strip()[:80]}")
            category_counts["OPEN mismatch"] += 1
            continue

        m = P_STUCK.search(line)
        if m:
            case_failures[current_case].append("Stuck (repeated clicks)")
            category_counts["Stuck (repeated clicks)"] += 1
            continue

        m = P_FALLBACK.search(line)
        if m:
            case_failures[current_case].append("Fallback triggered")
            category_counts["Fallback triggered"] += 1
            continue

    # Report
    print("=" * 60)
    print("Failure Category Summary")
    print("=" * 60)
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count}")
    print()

    if parse_fail_examples:
        print("-" * 60)
        print("Parser Failure Examples (first 20):")
        print("-" * 60)
        for ex in parse_fail_examples:
            print(ex)
        print()

    # Per-case breakdown for cases with failures
    if case_failures:
        print("-" * 60)
        print("Per-Case Failure Details:")
        print("-" * 60)
        for case, reasons in sorted(case_failures.items()):
            print(f"\n  [{case}]")
            for r in reasons:
                print(f"    - {r}")

    print(f"\nTotal cases with failures: {len(case_failures)}")
    print(f"Total failure events: {sum(category_counts.values())}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else LOG_FILE
    analyze(path)
