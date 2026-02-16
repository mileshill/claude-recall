#!/usr/bin/env python3
"""
Comprehensive test suite for the secret redaction module.

Tests:
1. Detection of known secret types (target: 95%+ detection rate)
2. False positive rate on legitimate data (target: < 5%)
3. Whitelist effectiveness
4. Shannon entropy detection
5. JSONL redaction
6. Performance (target: < 500ms per session)
7. Edge cases and robustness

Run: python3 test_redact_secrets.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Add the scripts directory to the path so we can import the module under test
scripts_dir = str(Path(__file__).parent.parent / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from redact_secrets import SecretRedactor, _shannon_entropy, _truncate_evidence


# ---------------------------------------------------------------------------
# Test fixtures: known secrets that MUST be detected
# ---------------------------------------------------------------------------

KNOWN_SECRETS = {
    "OpenAI API Key": "sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "Anthropic API Key": "sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "GitHub Personal Access Token": "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "GitHub Fine-Grained Token": "github_pat_11XXXXXX01234567890_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "GitHub App Token (ghs)": "ghs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "AWS Access Key ID": "AKIAIOSFODNN7EXAMPLE",
    "AWS Secret Access Key": 'aws_secret_access_key = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
    "Google API Key": "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "Google OAuth Client Secret": "GOCSPX-XXXXXXXXXXXXXXXXXXXXXXXX",
    "Slack Bot Token": "xoxb-XXXXXXXXXXXX-XXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXX",
    "Slack Webhook": "https://hooks.example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
    "Stripe Secret Key": "sk-live-XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "Stripe Test Key": "sk-test-XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "SendGrid API Key": "SG.XXXXXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXX",
    "SSH Private Key Header": "-----BEGIN RSA PRIVATE KEY-----",
    "SSH Private Key (OpenSSH)": "-----BEGIN OPENSSH PRIVATE KEY-----",
    "PGP Private Key Header": "-----BEGIN PGP PRIVATE KEY BLOCK-----",
    "PostgreSQL Connection String": "postgresql://admin:s3cr3tP@ss@db.example.com:5432/mydb",
    "MySQL Connection String": "mysql://root:password123@localhost:3306/appdb",
    "MongoDB Connection String": "mongodb+srv://user:hunter2@cluster0.mongodb.net",
    "Redis Connection String": "redis://:mysecretpassword@redis.example.com:6379",
    "npm Token": "npm_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "PyPI Token": "pypi-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "Bearer Token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.XXXXXXXXXXXXXX",
    "Generic Secret Assignment": 'api_key = "sk_real_secret_value_here_abc123"',
    "Discord Bot Token": "MTIzNDU2Nzg5.XXXXXX.YYYYYYYYYYYYYYYYYYYYYYYY",
    "Azure Storage Connection": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX;",
}

# ---------------------------------------------------------------------------
# Test fixtures: legitimate data that must NOT be flagged (false positives)
# ---------------------------------------------------------------------------

LEGITIMATE_DATA = {
    "UUID v4": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "UUID (uppercase)": "F47AC10B-58CC-4372-A567-0E02B2C3D479",
    "Git commit hash (short)": "a5c59f13",
    "Session ID (UUID)": "f56f063a-f80c-4f7c-80b8-0704b19422c2",
    "Regular text": "This is a normal conversation about implementing features.",
    "File path": "/Users/miles/PycharmProjects/pulseclaim-rapidflow/.claude/context/sessions/index.json",
    "CSS hex color": "#FF5733",
    "Git log line": "c52d31e0 debug(realtime): add comprehensive subscription status logging",
    "Placeholder token": "sk-your-api-key-here",
    "Example token": "ghp_yourGithubTokenHere",
    "Documentation placeholder": "REPLACE_ME_WITH_YOUR_KEY",
    "Normal variable assignment": 'name = "John Doe"',
    "Numeric string": "1234567890123456789012345678901234567890",
    "Normal URL": "https://api.example.com/v1/users/12345",
    "Supabase publishable key": "sb_publishable_abc123def456",
    "Markdown heading": "## Files Modified in This Session",
    "Package version": "rank-bm25>=0.2.2",
    "ISO timestamp": "2026-02-16T16:56:01.734791+00:00",
    "Regular code": "const result = await supabase.from('users').select('*');",
    "English paragraph": (
        "The quick brown fox jumps over the lazy dog. "
        "This is perfectly normal text that should not trigger any secret detection."
    ),
}


def test_known_secrets_detection():
    """
    Test that all known secret types are detected.
    Target: 95%+ detection rate.
    """
    print("\n=== Test: Known Secrets Detection ===\n")
    redactor = SecretRedactor()
    detected = 0
    missed = []

    for name, secret in KNOWN_SECRETS.items():
        # Embed the secret in a realistic context
        text = f"Here is some config: {secret} and more text after."
        redacted, report = redactor.redact(text)

        if report.total_findings > 0:
            detected += 1
            conf = report.findings[0].confidence.upper()
            print(f"  [PASS] {name}: detected ({conf})")
        else:
            missed.append(name)
            print(f"  [FAIL] {name}: NOT detected")

    total = len(KNOWN_SECRETS)
    rate = (detected / total) * 100 if total > 0 else 0
    print(f"\n  Detection rate: {detected}/{total} = {rate:.1f}%")
    print(f"  Target: >= 95%")

    if missed:
        print(f"  Missed: {', '.join(missed)}")

    return rate >= 95.0, rate, missed


def test_false_positive_rate():
    """
    Test that legitimate data is NOT flagged.
    Target: < 5% false positive rate.
    """
    print("\n=== Test: False Positive Rate ===\n")
    redactor = SecretRedactor()
    false_positives = []

    for name, data in LEGITIMATE_DATA.items():
        text = f"Context line: {data}"
        redacted, report = redactor.redact(text)

        if report.total_findings > 0:
            false_positives.append((name, report.findings[0].pattern_name))
            print(f"  [FAIL] {name}: falsely flagged as '{report.findings[0].pattern_name}'")
        else:
            print(f"  [PASS] {name}: correctly ignored")

    total = len(LEGITIMATE_DATA)
    fp_count = len(false_positives)
    fp_rate = (fp_count / total) * 100 if total > 0 else 0
    print(f"\n  False positive rate: {fp_count}/{total} = {fp_rate:.1f}%")
    print(f"  Target: < 5%")

    return fp_rate < 5.0, fp_rate, false_positives


def test_entropy_detection():
    """
    Test Shannon entropy detection for high-randomness strings.
    """
    print("\n=== Test: Shannon Entropy Detection ===\n")

    # High entropy strings (should be flagged)
    high_entropy = [
        "xK9mP2vQ7rT4wY6zA1cE3fG5hJ8kL0nO",  # Random alphanumeric
        "aB3cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV",  # Mixed case random
    ]

    # Low entropy strings (should NOT be flagged)
    low_entropy = [
        "aaaaaaaaaaaaaaaaaaaaaa",  # Repeated char
        "abcabcabcabcabcabcabc",  # Repeated pattern
        "the_quick_brown_fox_",  # English words
    ]

    redactor = SecretRedactor()
    results = {"correct": 0, "total": 0}

    for s in high_entropy:
        entropy = _shannon_entropy(s)
        text = f"token={s}"
        _, report = redactor.redact(text)
        flagged = report.total_findings > 0
        expected = True
        correct = flagged == expected
        results["total"] += 1
        if correct:
            results["correct"] += 1
        status = "PASS" if correct else "FAIL"
        print(f"  [{status}] High entropy '{s[:20]}...' (H={entropy:.2f}): flagged={flagged}")

    for s in low_entropy:
        entropy = _shannon_entropy(s)
        text = f"value={s}"
        _, report = redactor.redact(text)
        flagged = report.total_findings > 0
        expected = False
        correct = flagged == expected
        results["total"] += 1
        if correct:
            results["correct"] += 1
        status = "PASS" if correct else "FAIL"
        print(f"  [{status}] Low entropy '{s[:20]}...' (H={entropy:.2f}): flagged={flagged}")

    rate = (results["correct"] / results["total"]) * 100 if results["total"] > 0 else 0
    print(f"\n  Entropy accuracy: {results['correct']}/{results['total']} = {rate:.1f}%")
    return rate >= 80.0, rate


def test_redaction_replacement():
    """
    Test that secrets are properly replaced with [REDACTED:...] placeholders.
    """
    print("\n=== Test: Redaction Replacement ===\n")
    redactor = SecretRedactor()

    text = "My API key is sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ please don't share."
    redacted, report = redactor.redact(text)

    # The original secret must NOT appear in the output
    has_original = "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ" in redacted
    has_placeholder = "[REDACTED:" in redacted

    print(f"  Original text length: {len(text)}")
    print(f"  Redacted text length: {len(redacted)}")
    print(f"  Original secret removed: {not has_original}")
    print(f"  Placeholder inserted: {has_placeholder}")
    print(f"  Redacted output: {redacted[:100]}...")

    passed = (not has_original) and has_placeholder
    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_evidence_truncation():
    """
    Test that evidence strings in findings are < 25 chars.
    """
    print("\n=== Test: Evidence Truncation ===\n")
    redactor = SecretRedactor()

    all_short = True
    for name, secret in KNOWN_SECRETS.items():
        text = f"Secret: {secret}"
        _, report = redactor.redact(text)
        for f in report.findings:
            if len(f.evidence) >= 25:
                print(f"  [FAIL] {name}: evidence too long ({len(f.evidence)} chars): '{f.evidence}'")
                all_short = False
            else:
                print(f"  [PASS] {name}: evidence={len(f.evidence)} chars: '{f.evidence}'")

    print(f"\n  Result: {'PASS' if all_short else 'FAIL'}")
    return all_short


def test_jsonl_redaction():
    """
    Test redaction of JSONL transcript data.
    """
    print("\n=== Test: JSONL Redaction ===\n")
    redactor = SecretRedactor()

    # Create mock JSONL with embedded secrets
    entries = [
        {"role": "user", "content": "Set the OpenAI key to sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ"},
        {"role": "assistant", "content": "I've configured the API key. The database is at postgresql://admin:s3cr3tP@ss@db.example.com:5432/mydb"},
        {"role": "user", "content": [{"type": "text", "text": "Also use this GitHub token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"}]},
        {"role": "assistant", "content": "Configuration updated. No secrets here in this response."},
    ]

    jsonl_text = "\n".join(json.dumps(e) for e in entries)
    redacted_jsonl, report = redactor.redact_jsonl(jsonl_text)

    print(f"  Total findings: {report.total_findings}")
    print(f"  High confidence: {report.high_confidence}")
    print(f"  Medium confidence: {report.medium_confidence}")

    # Verify secrets are removed from output
    secrets_present = any(
        s in redacted_jsonl
        for s in [
            "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ",
            "s3cr3tP@ss",
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
        ]
    )
    print(f"  Secrets removed from output: {not secrets_present}")
    print(f"  Placeholders present: {'[REDACTED:' in redacted_jsonl}")

    # Verify output is still valid JSONL
    valid_jsonl = True
    for line in redacted_jsonl.splitlines():
        if line.strip():
            try:
                json.loads(line)
            except json.JSONDecodeError:
                valid_jsonl = False
                break
    print(f"  Output is valid JSONL: {valid_jsonl}")

    passed = (not secrets_present) and valid_jsonl and report.total_findings >= 3
    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_performance():
    """
    Test redaction performance.
    Target: < 500ms per session.
    """
    print("\n=== Test: Performance ===\n")
    redactor = SecretRedactor()

    # Build a realistic session text (~50KB with some secrets sprinkled in)
    base_text = "This is a normal line of session text discussing implementation details.\n" * 100
    secrets_text = "\n".join([
        f"Config value: {secret}" for secret in list(KNOWN_SECRETS.values())[:10]
    ])
    large_text = base_text + secrets_text + base_text

    print(f"  Text size: {len(large_text):,} chars ({len(large_text)/1024:.1f} KB)")

    # Run multiple iterations for reliable timing
    iterations = 10
    times = []
    for i in range(iterations):
        start = time.monotonic()
        _, report = redactor.redact(large_text)
        elapsed = (time.monotonic() - start) * 1000
        times.append(elapsed)

    avg_ms = sum(times) / len(times)
    max_ms = max(times)
    min_ms = min(times)

    print(f"  Iterations: {iterations}")
    print(f"  Average: {avg_ms:.1f}ms")
    print(f"  Min: {min_ms:.1f}ms")
    print(f"  Max: {max_ms:.1f}ms")
    print(f"  Target: < 500ms")

    passed = avg_ms < 500
    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed, avg_ms


def test_multi_secret_in_one_line():
    """
    Test detection of multiple secrets on a single line.
    """
    print("\n=== Test: Multiple Secrets Per Line ===\n")
    redactor = SecretRedactor()

    text = (
        'OPENAI_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ '
        'GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij '
        'AWS_KEY=AKIAIOSFODNN7EXAMPLE'
    )
    redacted, report = redactor.redact(text)

    print(f"  Input: {text[:80]}...")
    print(f"  Findings: {report.total_findings}")
    for f in report.findings:
        print(f"    - {f.pattern_name} ({f.confidence})")

    passed = report.total_findings >= 3
    print(f"\n  Result: {'PASS' if passed else 'FAIL'} (found {report.total_findings}/3 expected)")
    return passed


def test_empty_and_edge_cases():
    """
    Test edge cases: empty strings, None-like inputs, very long strings.
    """
    print("\n=== Test: Edge Cases ===\n")
    redactor = SecretRedactor()
    all_passed = True

    # Empty string
    redacted, report = redactor.redact("")
    ok = redacted == "" and report.total_findings == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Empty string")
    all_passed = all_passed and ok

    # Whitespace only
    redacted, report = redactor.redact("   \n\n   ")
    ok = report.total_findings == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Whitespace only")
    all_passed = all_passed and ok

    # Very long text without secrets
    long_text = "x" * 100000
    redacted, report = redactor.redact(long_text)
    ok = report.total_findings == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] 100K chars, no secrets")
    all_passed = all_passed and ok

    # Unicode text
    redacted, report = redactor.redact("Configuration terminee avec succes. Cle: rien de special.")
    ok = report.total_findings == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Unicode text")
    all_passed = all_passed and ok

    # Empty JSONL
    redacted, report = redactor.redact_jsonl("")
    ok = report.total_findings == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Empty JSONL")
    all_passed = all_passed and ok

    print(f"\n  Result: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


def test_report_structure():
    """
    Test that the redaction report has all expected fields.
    """
    print("\n=== Test: Report Structure ===\n")
    redactor = SecretRedactor()

    text = "Use this key: sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ"
    _, report = redactor.redact(text)

    report_dict = report.to_dict()
    required_fields = ["total_findings", "high_confidence", "medium_confidence",
                       "findings", "whitelisted_skips", "elapsed_ms", "text_length"]

    all_present = True
    for field in required_fields:
        present = field in report_dict
        if not present:
            all_present = False
        print(f"  [{'PASS' if present else 'FAIL'}] Report has '{field}'")

    # Check finding structure
    if report.findings:
        finding = report.findings[0]
        finding_fields = ["pattern_name", "category", "confidence", "evidence"]
        for field in finding_fields:
            present = hasattr(finding, field)
            if not present:
                all_present = False
            print(f"  [{'PASS' if present else 'FAIL'}] Finding has '{field}'")

    print(f"\n  Result: {'PASS' if all_present else 'FAIL'}")
    return all_present


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SECRET REDACTION TEST SUITE")
    print("=" * 70)

    results = {}

    # Core detection tests
    passed, rate, missed = test_known_secrets_detection()
    results["Known Secrets Detection"] = {"passed": passed, "detail": f"{rate:.1f}%"}

    passed, fp_rate, fps = test_false_positive_rate()
    results["False Positive Rate"] = {"passed": passed, "detail": f"{fp_rate:.1f}%"}

    # Feature tests
    passed, entropy_rate = test_entropy_detection()
    results["Entropy Detection"] = {"passed": passed, "detail": f"{entropy_rate:.1f}%"}

    passed = test_redaction_replacement()
    results["Redaction Replacement"] = {"passed": passed}

    passed = test_evidence_truncation()
    results["Evidence Truncation"] = {"passed": passed}

    passed = test_jsonl_redaction()
    results["JSONL Redaction"] = {"passed": passed}

    passed, avg_ms = test_performance()
    results["Performance"] = {"passed": passed, "detail": f"{avg_ms:.1f}ms"}

    passed = test_multi_secret_in_one_line()
    results["Multi-Secret Line"] = {"passed": passed}

    passed = test_empty_and_edge_cases()
    results["Edge Cases"] = {"passed": passed}

    passed = test_report_structure()
    results["Report Structure"] = {"passed": passed}

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r["passed"])

    for name, result in results.items():
        status = "PASS" if result["passed"] else "FAIL"
        detail = f" ({result['detail']})" if "detail" in result else ""
        print(f"  [{status}] {name}{detail}")

    print(f"\n  Total: {passed_tests}/{total_tests} passed")
    print("=" * 70)

    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
