"""
ConsoleAlerting adapter - Prints alerts to stdout for development.
"""

from typing import Any, Dict, Optional

from scraper.ports.alerting import Alerting
from scraper.domain.models import AlertSeverity


class ConsoleAlerting(Alerting):
    """Simple console-based alerting for development."""

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Print alert to stdout with appropriate emoji."""
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }

        emoji = emoji_map.get(severity, "ℹ️")
        print(f"{emoji} [{severity.value.upper()}] {title}")
        print(f"   {message}")

        if metadata:
            print(f"   Metadata: {metadata}")
