"""
Alert handling for quality check system.

Supports multiple alert methods:
- Log to file (always enabled)
- Print to stderr (interactive mode)
- Email (optional, SMTP config)
- Slack webhook (optional, webhook URL)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .checks import CheckResult


class AlertManager:
    """Manages alerting for quality check results."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager.

        Args:
            config: Configuration dictionary with alert settings
        """
        self.config = config or {}
        self.alert_log = Path(self.config.get(
            "alert_log_path",
            Path.home() / ".claude" / "context" / "sessions" / "quality_alerts.jsonl"
        ))

        # Alert history for deduplication
        self.alert_history = defaultdict(list)
        self._load_alert_history()

    def _load_alert_history(self):
        """Load recent alert history for deduplication."""
        if not self.alert_log.exists():
            return

        # Load last 100 alerts
        try:
            with open(self.alert_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-100:]:
                    try:
                        alert = json.loads(line.strip())
                        key = f"{alert['check_name']}:{alert['severity']}"
                        self.alert_history[key].append(alert['timestamp'])
                    except:
                        continue
        except Exception as e:
            print(f"Warning: Failed to load alert history: {e}", file=sys.stderr)

    def send_alerts(
        self,
        results: List[CheckResult],
        interactive: bool = True,
        email: Optional[str] = None,
    ):
        """
        Send alerts for failed checks.

        Args:
            results: List of CheckResult objects
            interactive: If True, print to stderr
            email: Optional email address to send alerts to
        """
        # Filter to failures only
        failed = [r for r in results if r.status in ("warning", "error")]

        if not failed:
            return

        # Deduplicate alerts
        deduplicated = self._deduplicate_alerts(failed)

        # Always log to file
        self._log_alerts(deduplicated)

        # Print to stderr if interactive
        if interactive:
            self._print_alerts(deduplicated)

        # Send email if configured
        if email and self.config.get("email_enabled"):
            self._send_email_alerts(deduplicated, email)

        # Send to Slack if configured
        if self.config.get("slack_webhook_url"):
            self._send_slack_alerts(deduplicated)

    def _deduplicate_alerts(
        self,
        results: List[CheckResult],
        window_minutes: int = 60
    ) -> List[CheckResult]:
        """
        Deduplicate alerts within time window.

        Args:
            results: List of CheckResult objects
            window_minutes: Time window for deduplication

        Returns:
            Deduplicated list of results
        """
        deduplicated = []
        current_time = datetime.now(timezone.utc)

        for result in results:
            key = f"{result.check_name}:{result.severity}"

            # Check if similar alert was sent recently
            recent_alerts = self.alert_history.get(key, [])
            if recent_alerts:
                # Parse most recent alert time
                try:
                    last_alert_str = recent_alerts[-1]
                    if last_alert_str.endswith('Z'):
                        last_alert = datetime.fromisoformat(last_alert_str.replace('Z', '+00:00'))
                    else:
                        last_alert = datetime.fromisoformat(last_alert_str)

                    time_diff = (current_time - last_alert).total_seconds() / 60

                    if time_diff < window_minutes:
                        # Skip duplicate
                        continue
                except:
                    pass

            # Add to deduplicated list
            deduplicated.append(result)

            # Update history
            self.alert_history[key].append(result.timestamp)

        return deduplicated

    def _log_alerts(self, results: List[CheckResult]):
        """Log alerts to file."""
        try:
            self.alert_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alert_log, 'a') as f:
                for result in results:
                    alert = {
                        "timestamp": result.timestamp,
                        "check_name": result.check_name,
                        "status": result.status,
                        "severity": result.severity,
                        "message": result.message,
                        "details": result.details,
                    }
                    f.write(json.dumps(alert) + "\n")
        except Exception as e:
            print(f"Warning: Failed to log alerts: {e}", file=sys.stderr)

    def _print_alerts(self, results: List[CheckResult]):
        """Print alerts to stderr."""
        if not results:
            return

        print("\n" + "=" * 60, file=sys.stderr)
        print("⚠️  QUALITY CHECK ALERTS", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        for result in results:
            # Icon based on severity
            if result.severity == "error":
                icon = "🔴"
            elif result.severity == "warning":
                icon = "⚠️"
            else:
                icon = "ℹ️"

            print(f"{icon} {result.check_name}", file=sys.stderr)
            print(f"   {result.message}", file=sys.stderr)

            # Print key details
            if result.details:
                for key, value in list(result.details.items())[:3]:  # First 3 details
                    print(f"   • {key}: {value}", file=sys.stderr)

            print("", file=sys.stderr)

    def _send_email_alerts(self, results: List[CheckResult], email: str):
        """
        Send email alerts.

        Args:
            results: List of CheckResult objects
            email: Email address to send to
        """
        # Email sending requires SMTP configuration
        smtp_config = self.config.get("smtp", {})
        if not smtp_config.get("server"):
            print("Warning: Email alerts enabled but SMTP not configured", file=sys.stderr)
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Build email body
            subject = f"Recall Quality Check Alerts ({len(results)} issues)"
            body_lines = [
                "Quality check alerts from Claude Recall Analytics:",
                "",
            ]

            for result in results:
                icon = "🔴" if result.severity == "error" else "⚠️"
                body_lines.append(f"{icon} {result.check_name}")
                body_lines.append(f"   {result.message}")
                body_lines.append("")

            body = "\n".join(body_lines)

            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config.get('from_address', 'recall@localhost')
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(smtp_config['server'], smtp_config.get('port', 587))
            if smtp_config.get('use_tls', True):
                server.starttls()
            if smtp_config.get('username') and smtp_config.get('password'):
                server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            server.quit()

            print(f"Email alerts sent to {email}", file=sys.stderr)

        except ImportError:
            print("Warning: Email support requires smtplib", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to send email alerts: {e}", file=sys.stderr)

    def _send_slack_alerts(self, results: List[CheckResult]):
        """
        Send Slack webhook alerts.

        Args:
            results: List of CheckResult objects
        """
        webhook_url = self.config.get("slack_webhook_url")
        if not webhook_url:
            return

        try:
            import urllib.request
            import urllib.parse

            # Build Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⚠️ Quality Check Alerts ({len(results)} issues)",
                    },
                },
            ]

            for result in results:
                icon = "🔴" if result.severity == "error" else "⚠️"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{icon} *{result.check_name}*\n{result.message}",
                    },
                })

            payload = {
                "blocks": blocks,
            }

            # Send request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
            )
            urllib.request.urlopen(req)

            print("Slack alerts sent", file=sys.stderr)

        except Exception as e:
            print(f"Warning: Failed to send Slack alerts: {e}", file=sys.stderr)

    def format_alert_summary(self, results: List[CheckResult]) -> str:
        """
        Format alert summary as string.

        Args:
            results: List of CheckResult objects

        Returns:
            Formatted summary
        """
        if not results:
            return "No alerts"

        lines = []
        errors = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]

        if errors:
            lines.append(f"🔴 {len(errors)} error(s):")
            for r in errors:
                lines.append(f"   • {r.check_name}: {r.message}")

        if warnings:
            lines.append(f"⚠️  {len(warnings)} warning(s):")
            for r in warnings:
                lines.append(f"   • {r.check_name}: {r.message}")

        return "\n".join(lines)
