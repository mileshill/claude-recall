#!/usr/bin/env python3
"""
Secret redaction module for session auto-capture.

Detects and redacts secrets from session text using:
1. Regex-based pattern matching (high confidence) from config/secret_patterns.json
2. Shannon entropy analysis (medium confidence) for high-randomness strings
3. Whitelist filtering to reduce false positives (UUIDs, hashes, placeholders)

Usage as module:
    from redact_secrets import SecretRedactor
    redactor = SecretRedactor()
    redacted_text, report = redactor.redact(text)

Usage standalone:
    echo "text with sk-abc123..." | python3 redact_secrets.py
    python3 redact_secrets.py --file input.txt
"""

import json
import math
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    """A single secret detection finding."""
    pattern_name: str
    category: str
    confidence: str
    evidence: str  # Truncated to < 25 chars for safety
    line_number: Optional[int] = None
    char_start: int = 0
    char_end: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RedactionReport:
    """Summary of redaction results for a single text block."""
    total_findings: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    findings: list = field(default_factory=list)
    whitelisted_skips: int = 0
    elapsed_ms: float = 0.0
    text_length: int = 0

    def to_dict(self) -> dict:
        result = asdict(self)
        result["findings"] = [f.to_dict() if isinstance(f, Finding) else f for f in self.findings]
        return result


def _truncate_evidence(match_text: str, max_len: int = 24) -> str:
    """
    Truncate a matched secret for safe evidence logging.
    Shows prefix + '***' + suffix, keeping total under max_len.
    """
    if len(match_text) <= max_len:
        # Even short matches get partial redaction for safety
        if len(match_text) <= 6:
            return match_text[:2] + "***"
        prefix_len = min(4, len(match_text) // 3)
        suffix_len = min(3, len(match_text) // 4)
        return match_text[:prefix_len] + "***" + match_text[-suffix_len:]

    prefix_len = min(6, max_len // 3)
    suffix_len = min(4, max_len // 4)
    return match_text[:prefix_len] + "***" + match_text[-suffix_len:]


def _shannon_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string.
    Higher entropy indicates more randomness (potential secret).

    Returns bits per character. Typical thresholds:
    - English text: ~3.5-4.0
    - Random alphanumeric: ~5.5-6.0
    - API keys/tokens: ~4.5-5.5
    """
    if not text:
        return 0.0

    freq = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1

    length = len(text)
    entropy = 0.0
    for count in freq.values():
        if count > 0:
            prob = count / length
            entropy -= prob * math.log2(prob)

    return entropy


class SecretRedactor:
    """
    Detects and redacts secrets from text using regex patterns and entropy analysis.

    Loads patterns from config/secret_patterns.json relative to this script's location.
    Applies whitelist patterns before flagging to reduce false positives.
    """

    # Regex to find candidate high-entropy tokens in text.
    # Matches sequences of alphanumeric + common token chars that are at least 16 chars long.
    _TOKEN_CANDIDATE_RE = re.compile(r'[A-Za-z0-9_/+=-]{16,}')

    # Redaction placeholder format
    _REDACTION_TEMPLATE = "[REDACTED:{name}]"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the redactor with patterns from the config file.

        Args:
            config_path: Path to secret_patterns.json. Defaults to
                         config/secret_patterns.json relative to this script.
        """
        if config_path is None:
            script_dir = Path(__file__).parent
            config_path = script_dir.parent / "config" / "secret_patterns.json"

        self._config_path = Path(config_path)
        self._patterns = []
        self._whitelist = []
        self._entropy_config = {"enabled": True, "min_length": 16, "threshold": 4.5}

        self._load_config()

    def _load_config(self):
        """Load and compile regex patterns from the configuration file."""
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Secret patterns config not found: {self._config_path}\n"
                f"Expected at: .claude/skills/recall/config/secret_patterns.json"
            )

        with open(self._config_path, "r") as f:
            config = json.load(f)

        # Compile detection patterns
        for p in config.get("patterns", []):
            try:
                compiled = re.compile(p["regex"])
                self._patterns.append({
                    "name": p["name"],
                    "regex": compiled,
                    "confidence": p.get("confidence", "medium"),
                    "category": p.get("category", "unknown"),
                })
            except re.error as e:
                print(
                    f"WARNING: Invalid regex for pattern '{p['name']}': {e}",
                    file=sys.stderr,
                )

        # Compile whitelist patterns
        for w in config.get("whitelist", []):
            try:
                compiled = re.compile(w["regex"])
                self._whitelist.append({
                    "name": w["name"],
                    "regex": compiled,
                    "description": w.get("description", ""),
                })
            except re.error as e:
                print(
                    f"WARNING: Invalid whitelist regex for '{w['name']}': {e}",
                    file=sys.stderr,
                )

        # Load entropy config
        entropy_cfg = config.get("entropy", {})
        if entropy_cfg:
            self._entropy_config.update(entropy_cfg)

    def _is_whitelisted(self, match_text: str) -> bool:
        """
        Check if a matched string is whitelisted (known false positive).

        Args:
            match_text: The matched text to check.

        Returns:
            True if the match should be skipped (whitelisted).
        """
        for w in self._whitelist:
            if w["regex"].fullmatch(match_text) or w["regex"].search(match_text):
                return True
        return False

    def _detect_by_patterns(self, text: str) -> list[tuple[int, int, dict]]:
        """
        Run all regex patterns against the text.

        Returns:
            List of (start, end, pattern_info) tuples for each match.
        """
        detections = []
        for pattern in self._patterns:
            for match in pattern["regex"].finditer(text):
                match_text = match.group(0)
                if self._is_whitelisted(match_text):
                    continue
                detections.append((
                    match.start(),
                    match.end(),
                    {
                        "name": pattern["name"],
                        "category": pattern["category"],
                        "confidence": pattern["confidence"],
                        "match_text": match_text,
                    },
                ))
        return detections

    def _detect_by_entropy(self, text: str) -> list[tuple[int, int, dict]]:
        """
        Find high-entropy token candidates that were not caught by regex patterns.

        Returns:
            List of (start, end, pattern_info) tuples for each high-entropy match.
        """
        if not self._entropy_config.get("enabled", True):
            return []

        min_length = self._entropy_config.get("min_length", 16)
        threshold = self._entropy_config.get("threshold", 4.5)

        detections = []
        for match in self._TOKEN_CANDIDATE_RE.finditer(text):
            candidate = match.group(0)

            if len(candidate) < min_length:
                continue

            if self._is_whitelisted(candidate):
                continue

            entropy = _shannon_entropy(candidate)
            if entropy >= threshold:
                detections.append((
                    match.start(),
                    match.end(),
                    {
                        "name": f"High-Entropy String (H={entropy:.2f})",
                        "category": "entropy",
                        "confidence": "medium",
                        "match_text": candidate,
                    },
                ))
        return detections

    def redact(self, text: str) -> tuple[str, RedactionReport]:
        """
        Detect and redact secrets from the given text.

        Applies regex pattern matching first, then entropy-based detection on
        remaining unmatched regions. Whitelist patterns are applied to reduce
        false positives.

        Args:
            text: The input text to scan and redact.

        Returns:
            A tuple of (redacted_text, report) where report contains details
            of all findings.
        """
        start_time = time.monotonic()
        report = RedactionReport(text_length=len(text))

        if not text:
            report.elapsed_ms = (time.monotonic() - start_time) * 1000
            return text, report

        # Phase 1: Regex-based detection
        regex_detections = self._detect_by_patterns(text)

        # Phase 2: Entropy-based detection
        entropy_detections = self._detect_by_entropy(text)

        # Merge detections, removing entropy detections that overlap with regex ones.
        # Regex patterns are more specific, so they take priority.
        all_detections = list(regex_detections)
        regex_ranges = set()
        for start, end, _ in regex_detections:
            for i in range(start, end):
                regex_ranges.add(i)

        for start, end, info in entropy_detections:
            # Only add if not already covered by a regex detection
            overlap = any(i in regex_ranges for i in range(start, end))
            if not overlap:
                all_detections.append((start, end, info))

        # Sort by position (descending) so we can replace from end to start
        # without invalidating earlier positions
        all_detections.sort(key=lambda d: d[0], reverse=True)

        # Deduplicate overlapping detections (keep the longer/earlier one)
        deduped = []
        covered_up_to = len(text)  # We process from end to start
        for start, end, info in all_detections:
            if end <= covered_up_to:
                deduped.append((start, end, info))
                covered_up_to = start

        # Build findings and perform redaction
        redacted = text
        for start, end, info in deduped:
            match_text = info["match_text"]
            evidence = _truncate_evidence(match_text)

            finding = Finding(
                pattern_name=info["name"],
                category=info["category"],
                confidence=info["confidence"],
                evidence=evidence,
                char_start=start,
                char_end=end,
            )
            report.findings.append(finding)

            if info["confidence"] == "high":
                report.high_confidence += 1
            else:
                report.medium_confidence += 1

            # Replace the secret with a redaction placeholder
            placeholder = self._REDACTION_TEMPLATE.format(name=info["name"])
            redacted = redacted[:start] + placeholder + redacted[end:]

        report.total_findings = len(report.findings)
        report.elapsed_ms = (time.monotonic() - start_time) * 1000

        # Add line numbers to findings (calculated from original text)
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == '\n':
                line_starts.append(i + 1)

        for finding in report.findings:
            for line_num, line_start in enumerate(line_starts, 1):
                if line_start > finding.char_start:
                    finding.line_number = line_num - 1
                    break
            else:
                finding.line_number = len(line_starts)

        return redacted, report

    def redact_jsonl(self, jsonl_text: str) -> tuple[str, RedactionReport]:
        """
        Redact secrets from JSONL-formatted transcript data.

        Processes each line independently to preserve JSON structure.
        Aggregates findings into a single report.

        Args:
            jsonl_text: The JSONL content (one JSON object per line).

        Returns:
            A tuple of (redacted_jsonl, aggregate_report).
        """
        start_time = time.monotonic()
        aggregate_report = RedactionReport(text_length=len(jsonl_text))
        redacted_lines = []

        for line_num, line in enumerate(jsonl_text.splitlines(), 1):
            if not line.strip():
                redacted_lines.append(line)
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # Not valid JSON; redact the raw text
                redacted_line, line_report = self.redact(line)
                redacted_lines.append(redacted_line)
                self._merge_report(aggregate_report, line_report, line_num)
                continue

            # Redact the 'content' field of transcript entries
            content = entry.get("content", "")
            if isinstance(content, str) and content:
                redacted_content, line_report = self.redact(content)
                entry["content"] = redacted_content
                self._merge_report(aggregate_report, line_report, line_num)
            elif isinstance(content, list):
                # Content can be a list of blocks (e.g., text blocks)
                for i, block in enumerate(content):
                    if isinstance(block, dict):
                        block_text = block.get("text", "")
                        if block_text:
                            redacted_block, block_report = self.redact(block_text)
                            block["text"] = redacted_block
                            self._merge_report(aggregate_report, block_report, line_num)

            redacted_lines.append(json.dumps(entry, ensure_ascii=False))

        aggregate_report.elapsed_ms = (time.monotonic() - start_time) * 1000
        return "\n".join(redacted_lines), aggregate_report

    @staticmethod
    def _merge_report(
        aggregate: RedactionReport, line_report: RedactionReport, line_num: int
    ):
        """Merge a per-line report into the aggregate report."""
        for finding in line_report.findings:
            finding.line_number = line_num
            aggregate.findings.append(finding)
        aggregate.total_findings += line_report.total_findings
        aggregate.high_confidence += line_report.high_confidence
        aggregate.medium_confidence += line_report.medium_confidence
        aggregate.whitelisted_skips += line_report.whitelisted_skips


def main():
    """CLI entry point for standalone redaction."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect and redact secrets from text."
    )
    parser.add_argument(
        "--file", "-f",
        help="Input file to redact. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Treat input as JSONL (one JSON object per line).",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only print the findings report (do not output redacted text).",
    )
    parser.add_argument(
        "--config",
        help="Path to secret_patterns.json config file.",
    )
    args = parser.parse_args()

    # Read input
    if args.file:
        with open(args.file, "r") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    # Initialize redactor
    redactor = SecretRedactor(config_path=args.config)

    # Redact
    if args.jsonl:
        redacted, report = redactor.redact_jsonl(text)
    else:
        redacted, report = redactor.redact(text)

    # Output
    if args.report_only:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(redacted)
        if report.total_findings > 0:
            print(
                f"\n--- Redaction Report ---\n"
                f"Findings: {report.total_findings} "
                f"(high: {report.high_confidence}, medium: {report.medium_confidence})\n"
                f"Elapsed: {report.elapsed_ms:.1f}ms\n",
                file=sys.stderr,
            )
            for f in report.findings:
                print(
                    f"  [{f.confidence.upper()}] {f.pattern_name}: {f.evidence}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    main()
