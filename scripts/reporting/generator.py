"""
Report generator for recall analytics.

Orchestrates data aggregation and formatting to produce reports.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from .aggregator import DataAggregator
from .formatters import MarkdownFormatter, JSONFormatter, HTMLFormatter

# Optional Jinja2 support
try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class ReportGenerator:
    """Main report generator class."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize report generator.

        Args:
            sessions_dir: Path to sessions directory. If None, uses default.
        """
        if sessions_dir is None:
            # Default to .claude/context/sessions
            home = Path.home()
            sessions_dir = home / ".claude" / "context" / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.aggregator = DataAggregator(self.sessions_dir)

        # Set up Jinja2 templates if available
        self.jinja_env = None
        if JINJA2_AVAILABLE:
            templates_dir = Path(__file__).parent / "templates"
            if templates_dir.exists():
                self.jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with data.

        Args:
            template_name: Name of template file
            data: Data to pass to template

        Returns:
            Rendered template string
        """
        if not self.jinja_env:
            raise RuntimeError("Jinja2 templates not available. Install jinja2: pip install jinja2")

        try:
            template = self.jinja_env.get_template(template_name)
            # Add generation timestamp
            render_data = dict(data)
            render_data['generation_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return template.render(**render_data)
        except TemplateNotFound:
            raise FileNotFoundError(f"Template not found: {template_name}")

    def generate_report(
        self,
        period_days: int = 30,
        format: str = "markdown",
        output_path: Optional[Path] = None,
        sections: Optional[List[str]] = None,
        use_template: bool = True,
    ) -> str:
        """
        Generate a complete analytics report.

        Args:
            period_days: Number of days to include in report
            format: Output format ("markdown", "json", "html", "email")
            output_path: Optional path to write report to
            sections: Optional list of sections to include (None = all)
            use_template: If True, use Jinja2 template (if available)

        Returns:
            Formatted report as string
        """
        # Aggregate data
        data = self.aggregator.generate_report_data(period_days)

        # Filter sections if specified
        if sections:
            filtered_data = {
                "period": data["period"],
            }
            for section in sections:
                if section in data:
                    filtered_data[section] = data[section]
            data = filtered_data

        # Format output
        if format == "json":
            report = JSONFormatter.format(data)
        elif format == "html":
            report = HTMLFormatter.format(data)
        elif format == "email" and use_template and self.jinja_env:
            # Use email template
            report = self._render_template("email.md.jinja2", data)
        elif format in ("markdown", "email"):
            # Try template first, fallback to formatter
            if use_template and self.jinja_env:
                try:
                    report = self._render_template("full_report.md.jinja2", data)
                except (FileNotFoundError, RuntimeError):
                    report = MarkdownFormatter.format(data, full=True)
            else:
                report = MarkdownFormatter.format(data, full=True)
        else:
            report = MarkdownFormatter.format(data, full=True)

        # Write to file if specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)

        return report

    def generate_summary(self, period_days: int = 7, use_template: bool = True) -> str:
        """
        Generate a brief summary report.

        Args:
            period_days: Number of days to include (default 7)
            use_template: If True, use Jinja2 template (if available)

        Returns:
            Brief markdown summary
        """
        data = self.aggregator.generate_report_data(period_days)

        # Try template first, fallback to formatter
        if use_template and self.jinja_env:
            try:
                return self._render_template("summary.md.jinja2", data)
            except (FileNotFoundError, RuntimeError):
                pass

        return MarkdownFormatter.format(data, full=False)

    def get_raw_data(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Get raw aggregated data without formatting.

        Args:
            period_days: Number of days to include

        Returns:
            Dictionary with aggregated metrics
        """
        return self.aggregator.generate_report_data(period_days)

    def export_json(self, period_days: int = 30, output_path: Path = None) -> str:
        """
        Export data as JSON.

        Args:
            period_days: Number of days to include
            output_path: Optional path to write JSON to

        Returns:
            JSON string
        """
        return self.generate_report(
            period_days=period_days,
            format="json",
            output_path=output_path,
        )

    def export_html(self, period_days: int = 30, output_path: Path = None) -> str:
        """
        Export data as HTML.

        Args:
            period_days: Number of days to include
            output_path: Optional path to write HTML to

        Returns:
            HTML string
        """
        return self.generate_report(
            period_days=period_days,
            format="html",
            output_path=output_path,
        )
