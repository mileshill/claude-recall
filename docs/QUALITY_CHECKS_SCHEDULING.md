# Quality Checks Scheduling Guide

This guide explains how to set up automated quality checks for Claude Recall Analytics.

## Overview

Quality checks can be run:
- **On-demand**: Manually when needed
- **Scheduled**: Automatically at regular intervals
- **Triggered**: On specific events (e.g., session start)

## Option 1: Cron (Recommended for Linux/macOS)

### Daily Checks

Add to your crontab (`crontab -e`):

```bash
# Run quality checks daily at 8 AM
0 8 * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --quick >> /tmp/recall_checks.log 2>&1
```

### Hourly Checks

```bash
# Run quality checks every hour
0 * * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --quick --no-alerts >> /tmp/recall_checks.log 2>&1
```

### With Email Alerts

```bash
# Run checks daily and send email alerts
0 8 * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --email your@email.com >> /tmp/recall_checks.log 2>&1
```

## Option 2: Claude Code Hooks

You can trigger quality checks automatically when starting a Claude session.

### SessionStart Hook

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": "cd ~/.claude/shared/recall && python3 scripts/run_quality_checks.py --quick --no-alerts"
  }
}
```

This runs a quick check every time you start a new Claude session.

### SessionEnd Hook

```json
{
  "hooks": {
    "SessionEnd": "cd ~/.claude/shared/recall && python3 scripts/run_quality_checks.py --hours 2"
  }
}
```

This checks data from the last 2 hours after each session ends.

## Option 3: Systemd Timer (Linux)

### Create Service File

Create `/etc/systemd/system/recall-quality-checks.service`:

```ini
[Unit]
Description=Recall Quality Checks
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/recall
ExecStart=/usr/bin/python3 scripts/run_quality_checks.py --quick
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Create Timer File

Create `/etc/systemd/system/recall-quality-checks.timer`:

```ini
[Unit]
Description=Run Recall Quality Checks Hourly
Requires=recall-quality-checks.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=recall-quality-checks.service

[Install]
WantedBy=timers.target
```

### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable recall-quality-checks.timer
sudo systemctl start recall-quality-checks.timer

# Check status
sudo systemctl status recall-quality-checks.timer
```

## Option 4: Monitor Mode

Run quality checks in continuous monitor mode:

```bash
# Terminal 1: Start monitor (checks every hour)
python3 scripts/run_quality_checks.py --monitor --interval 3600

# Or run in background
nohup python3 scripts/run_quality_checks.py --monitor --interval 3600 &
```

This keeps a process running that performs checks at regular intervals.

## Check Configuration

Configure check thresholds in `config/analytics_config.json`:

```json
{
  "quality_checks": {
    "enabled": true,
    "schedule": "0 8 * * *",
    "LowRelevanceCheck": {
      "low_score_threshold": 0.4,
      "warning_percent": 0.2
    },
    "NoResultsCheck": {
      "no_results_threshold_percent": 0.3
    },
    "HighLatencyCheck": {
      "high_latency_ms": 1000,
      "warning_percent": 0.1
    },
    "UsageAnomalyCheck": {
      "spike_threshold": 3.0
    },
    "alerts": {
      "email_enabled": false,
      "slack_webhook_url": ""
    }
  }
}
```

## Alert Configuration

### Email Alerts (SMTP)

Add SMTP configuration to `analytics_config.json`:

```json
{
  "quality_checks": {
    "alerts": {
      "email_enabled": true,
      "smtp": {
        "server": "smtp.gmail.com",
        "port": 587,
        "use_tls": true,
        "username": "your-email@gmail.com",
        "password": "your-app-password",
        "from_address": "recall-alerts@yourdomain.com"
      }
    }
  }
}
```

Then run with `--email your@email.com`.

### Slack Alerts

Add Slack webhook to configuration:

```json
{
  "quality_checks": {
    "alerts": {
      "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    }
  }
}
```

Alerts will be sent to Slack automatically when checks fail.

## Recommended Schedules

### Development/Testing
- **Frequency**: Every 2-4 hours
- **Mode**: `--quick` (skip expensive checks)
- **Alerts**: Log only (`--no-alerts`)

```bash
# Every 4 hours
0 */4 * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --quick --no-alerts
```

### Production
- **Frequency**: Every 1 hour
- **Mode**: Full checks
- **Alerts**: Enabled with email/Slack

```bash
# Every hour
0 * * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --email admin@company.com
```

### Critical Systems
- **Frequency**: Every 15 minutes
- **Mode**: `--quick`
- **Alerts**: Immediate (Slack + email)

```bash
# Every 15 minutes
*/15 * * * * cd /path/to/recall && python3 scripts/run_quality_checks.py --quick --email admin@company.com
```

## Viewing Results

### Check Logs

Quality check results are logged to:
```
~/.claude/context/sessions/quality_check_log.jsonl
```

View recent checks:
```bash
tail -20 ~/.claude/context/sessions/quality_check_log.jsonl | jq .
```

### Alert Log

Alerts are logged separately to:
```
~/.claude/context/sessions/quality_alerts.jsonl
```

View recent alerts:
```bash
tail -10 ~/.claude/context/sessions/quality_alerts.jsonl | jq .
```

### Summary Report

Get a quick summary:
```bash
python3 scripts/run_quality_checks.py --quick
```

## Troubleshooting

### Checks Not Running

1. **Verify cron is running**: `systemctl status cron` (Linux) or `sudo launchctl list | grep cron` (macOS)
2. **Check cron logs**: `grep CRON /var/log/syslog` (Linux) or `log show --predicate 'process == "cron"' --last 1h` (macOS)
3. **Test command manually**: Run the exact command from your cron entry

### No Alerts Received

1. **Check alert configuration**: Verify SMTP/Slack settings in config
2. **Test alert manually**: Run with known failure to trigger alert
3. **Check alert log**: Verify alerts are being logged to file

### High False Positive Rate

1. **Adjust thresholds**: Tune check configurations in `analytics_config.json`
2. **Use quick mode**: Skip expensive checks if not needed
3. **Increase check intervals**: Run less frequently to reduce noise

## Best Practices

1. **Start conservative**: Begin with `--quick` and infrequent checks
2. **Tune thresholds**: Adjust based on your usage patterns
3. **Monitor alert volume**: Too many alerts = alert fatigue
4. **Use deduplication**: Built-in 60-minute window prevents spam
5. **Review regularly**: Check logs weekly to identify trends

## Examples

### Minimal Setup (Cron)
```bash
# Daily quick check
0 8 * * * cd ~/.claude/shared/recall && python3 scripts/run_quality_checks.py --quick
```

### Full Production Setup (Cron + Email)
```bash
# Hourly checks with email
0 * * * * cd ~/.claude/shared/recall && python3 scripts/run_quality_checks.py --email admin@company.com

# Daily full report
0 9 * * * cd ~/.claude/shared/recall && python3 scripts/generate_recall_report.py --summary --email admin@company.com
```

### Development Setup (Hook)
```json
{
  "hooks": {
    "SessionStart": "cd ~/.claude/shared/recall && python3 scripts/run_quality_checks.py --quick --no-alerts"
  }
}
```
