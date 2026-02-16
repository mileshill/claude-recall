"""
Output formatters for recall analytics reports.

Supports Markdown, JSON, and HTML output with ASCII charts and tables.
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class ASCIIChart:
    """Simple ASCII chart generator."""

    @staticmethod
    def bar_chart(data: Dict[str, float], max_width: int = 40) -> str:
        """
        Generate horizontal bar chart.

        Args:
            data: Dictionary of label -> value
            max_width: Maximum bar width in characters

        Returns:
            ASCII bar chart as string
        """
        if not data:
            return "No data"

        max_value = max(data.values()) if data else 1
        lines = []

        for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            bar_width = int((value / max_value) * max_width) if max_value > 0 else 0
            bar = "█" * bar_width
            lines.append(f"{label:20s} {bar} {value}")

        return "\n".join(lines)

    @staticmethod
    def sparkline(values: List[float]) -> str:
        """
        Generate sparkline from list of values.

        Args:
            values: List of numeric values

        Returns:
            Sparkline string
        """
        if not values:
            return ""

        sparks = "▁▂▃▄▅▆▇█"
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val > min_val else 1

        sparkline = ""
        for v in values:
            index = int(((v - min_val) / range_val) * (len(sparks) - 1))
            sparkline += sparks[index]

        return sparkline


class MarkdownFormatter:
    """Format report data as Markdown."""

    @staticmethod
    def format(data: Dict[str, Any], full: bool = True) -> str:
        """
        Format report data as Markdown.

        Args:
            data: Aggregated report data
            full: If True, include all sections. If False, brief summary only.

        Returns:
            Markdown formatted report
        """
        if full:
            return MarkdownFormatter._format_full_report(data)
        else:
            return MarkdownFormatter._format_summary(data)

    @staticmethod
    def _format_full_report(data: Dict[str, Any]) -> str:
        """Generate full Markdown report."""
        sections = []

        # Header
        sections.append("# Recall Analytics Report")
        sections.append("")
        sections.append(f"**Period:** {data['period']['days']} days")
        sections.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append("")

        # Executive Summary
        sections.append("## Executive Summary")
        sections.append("")
        usage = data['usage']
        quality = data['quality']
        impact = data['impact']

        sections.append(f"- **Total Searches:** {usage['total_searches']}")
        sections.append(f"- **Unique Sessions:** {usage['unique_sessions']}")
        sections.append(f"- **Average Quality Score:** {quality['overall_score']:.3f}")
        sections.append(f"- **Average Time Saved:** {impact['avg_efficiency_gain']:.1f} minutes per session")
        sections.append("")

        # Usage Statistics
        sections.append("## Usage Statistics")
        sections.append("")
        sections.append(f"- Total searches: {usage['total_searches']}")
        sections.append(f"- Searches per day: {usage['searches_per_day']:.2f}")
        sections.append(f"- Average results per search: {usage['avg_results_per_search']:.2f}")
        sections.append("")

        if usage['mode_distribution']:
            sections.append("### Search Mode Distribution")
            sections.append("```")
            sections.append(ASCIIChart.bar_chart(usage['mode_distribution']))
            sections.append("```")
            sections.append("")

        # Quality Metrics
        sections.append("## Quality Metrics")
        sections.append("")
        sections.append(f"- Total evaluations: {quality['total_evaluations']}")
        sections.append(f"- Overall score: {quality['overall_score']:.3f}")
        sections.append(f"- Relevance: {quality['avg_relevance']:.3f}")
        sections.append(f"- Coverage: {quality['avg_coverage']:.3f}")
        sections.append(f"- Specificity: {quality['avg_specificity']:.3f}")
        sections.append("")

        if quality['score_distribution']:
            sections.append("### Score Distribution")
            sections.append("```")
            sections.append(ASCIIChart.bar_chart(quality['score_distribution']))
            sections.append("```")
            sections.append("")

        # Impact Analysis
        sections.append("## Context Impact Analysis")
        sections.append("")
        sections.append(f"- Total analyses: {impact['total_analyses']}")
        sections.append(f"- Average explicit citations: {impact['avg_explicit_citations']:.2f}")
        sections.append(f"- Average implicit usage score: {impact['avg_implicit_usage']:.3f}")
        sections.append(f"- Average continuity score: {impact['avg_continuity_score']:.3f}")
        sections.append(f"- Average efficiency gain: {impact['avg_efficiency_gain']:.1f} minutes")
        sections.append("")

        # Top Sessions
        top_sessions = data['top_sessions']
        if top_sessions:
            sections.append("## Most Valuable Sessions")
            sections.append("")
            sections.append("| Rank | Session ID | Continuity | Time Saved (min) | Citations |")
            sections.append("|------|------------|------------|------------------|-----------|")
            for i, session in enumerate(top_sessions[:5], 1):
                sections.append(
                    f"| {i} | `{session['session_id'][:8]}...` | "
                    f"{session['avg_continuity']:.3f} | "
                    f"{session['time_saved_minutes']:.1f} | "
                    f"{session['total_citations']} |"
                )
            sections.append("")

        # Performance
        perf = data['performance']
        sections.append("## Performance Benchmarks")
        sections.append("")
        sections.append(f"- Average latency: {perf['avg_latency_ms']:.2f}ms")
        sections.append(f"- P50 latency: {perf['p50_latency_ms']:.2f}ms")
        sections.append(f"- P95 latency: {perf['p95_latency_ms']:.2f}ms")
        sections.append(f"- P99 latency: {perf['p99_latency_ms']:.2f}ms")
        sections.append(f"- Cache hit rate: {perf['cache_hit_rate']:.1%}")
        sections.append("")

        # Issues and Recommendations
        issues = data['issues']
        if issues:
            sections.append("## Issues & Recommendations")
            sections.append("")
            for issue in issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "⚠️",
                    "info": "ℹ️",
                }.get(issue['severity'], "•")
                sections.append(f"### {severity_icon} {issue['category'].title()}")
                sections.append("")
                sections.append(f"**Issue:** {issue['message']}")
                sections.append("")
                sections.append(f"**Recommendation:** {issue['recommendation']}")
                sections.append("")

        # Cost Analysis
        costs = data['costs']
        if costs['total_evaluations'] > 0:
            sections.append("## Cost Analysis")
            sections.append("")
            sections.append(f"- Total evaluations: {costs['total_evaluations']}")
            sections.append(f"- Total cost: ${costs['total_cost_usd']:.4f}")
            sections.append(f"- Average cost per evaluation: ${costs['avg_cost_per_eval']:.6f}")
            sections.append(f"- Total tokens: {costs['total_tokens']:,}")
            sections.append("")

        return "\n".join(sections)

    @staticmethod
    def _format_summary(data: Dict[str, Any]) -> str:
        """Generate brief summary."""
        sections = []

        sections.append("# Recall Analytics Summary")
        sections.append("")
        sections.append(f"**Period:** Last {data['period']['days']} days")
        sections.append("")

        usage = data['usage']
        quality = data['quality']
        impact = data['impact']
        perf = data['performance']

        sections.append("## Quick Stats")
        sections.append("")
        sections.append(f"- 🔍 {usage['total_searches']} searches across {usage['unique_sessions']} sessions")
        sections.append(f"- ⭐ Quality score: {quality['overall_score']:.3f}/1.0")
        sections.append(f"- ⚡ Average latency: {perf['avg_latency_ms']:.0f}ms")
        sections.append(f"- 💾 Cache hit rate: {perf['cache_hit_rate']:.1%}")
        sections.append(f"- ⏱️  Time saved: {impact['avg_efficiency_gain']:.1f} min/session")
        sections.append("")

        # Issues
        issues = data['issues']
        if issues:
            sections.append("## Alerts")
            for issue in issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "⚠️",
                    "info": "ℹ️",
                }.get(issue['severity'], "•")
                sections.append(f"- {severity_icon} {issue['message']}")
            sections.append("")
        else:
            sections.append("✅ No issues detected")
            sections.append("")

        return "\n".join(sections)


class JSONFormatter:
    """Format report data as JSON."""

    @staticmethod
    def format(data: Dict[str, Any]) -> str:
        """
        Format report data as JSON.

        Args:
            data: Aggregated report data

        Returns:
            JSON formatted report
        """
        # Add metadata
        output = {
            "generated_at": datetime.now().isoformat(),
            "report_data": data,
        }

        return json.dumps(output, indent=2, default=str)


class HTMLFormatter:
    """Format report data as HTML."""

    @staticmethod
    def format(data: Dict[str, Any]) -> str:
        """
        Format report data as HTML.

        Args:
            data: Aggregated report data

        Returns:
            HTML formatted report
        """
        usage = data['usage']
        quality = data['quality']
        impact = data['impact']
        perf = data['performance']

        html_parts = []
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html>")
        html_parts.append("<head>")
        html_parts.append("  <meta charset='utf-8'>")
        html_parts.append("  <title>Recall Analytics Report</title>")
        html_parts.append("  <style>")
        html_parts.append("    body { font-family: sans-serif; margin: 40px; }")
        html_parts.append("    h1 { color: #333; }")
        html_parts.append("    h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }")
        html_parts.append("    .metric { display: inline-block; margin: 10px 20px; }")
        html_parts.append("    .metric-value { font-size: 2em; font-weight: bold; color: #0066cc; }")
        html_parts.append("    .metric-label { font-size: 0.9em; color: #666; }")
        html_parts.append("    table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
        html_parts.append("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html_parts.append("    th { background-color: #f2f2f2; }")
        html_parts.append("    .issue { margin: 20px 0; padding: 15px; border-left: 4px solid #ff9800; background: #fff3cd; }")
        html_parts.append("  </style>")
        html_parts.append("</head>")
        html_parts.append("<body>")

        # Header
        html_parts.append(f"  <h1>Recall Analytics Report</h1>")
        html_parts.append(f"  <p><strong>Period:</strong> {data['period']['days']} days</p>")
        html_parts.append(f"  <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        # Metrics
        html_parts.append("  <h2>Key Metrics</h2>")
        html_parts.append("  <div>")
        html_parts.append(f"    <div class='metric'>")
        html_parts.append(f"      <div class='metric-value'>{usage['total_searches']}</div>")
        html_parts.append(f"      <div class='metric-label'>Total Searches</div>")
        html_parts.append(f"    </div>")
        html_parts.append(f"    <div class='metric'>")
        html_parts.append(f"      <div class='metric-value'>{quality['overall_score']:.3f}</div>")
        html_parts.append(f"      <div class='metric-label'>Quality Score</div>")
        html_parts.append(f"    </div>")
        html_parts.append(f"    <div class='metric'>")
        html_parts.append(f"      <div class='metric-value'>{perf['avg_latency_ms']:.0f}ms</div>")
        html_parts.append(f"      <div class='metric-label'>Avg Latency</div>")
        html_parts.append(f"    </div>")
        html_parts.append("  </div>")

        # Top Sessions
        if data['top_sessions']:
            html_parts.append("  <h2>Top Sessions</h2>")
            html_parts.append("  <table>")
            html_parts.append("    <tr><th>Session ID</th><th>Continuity</th><th>Time Saved (min)</th><th>Citations</th></tr>")
            for session in data['top_sessions'][:5]:
                html_parts.append("    <tr>")
                html_parts.append(f"      <td><code>{session['session_id'][:16]}</code></td>")
                html_parts.append(f"      <td>{session['avg_continuity']:.3f}</td>")
                html_parts.append(f"      <td>{session['time_saved_minutes']:.1f}</td>")
                html_parts.append(f"      <td>{session['total_citations']}</td>")
                html_parts.append("    </tr>")
            html_parts.append("  </table>")

        # Issues
        if data['issues']:
            html_parts.append("  <h2>Issues & Recommendations</h2>")
            for issue in data['issues']:
                html_parts.append("  <div class='issue'>")
                html_parts.append(f"    <strong>{issue['category'].title()}:</strong> {issue['message']}<br>")
                html_parts.append(f"    <strong>Recommendation:</strong> {issue['recommendation']}")
                html_parts.append("  </div>")

        html_parts.append("</body>")
        html_parts.append("</html>")

        return "\n".join(html_parts)
