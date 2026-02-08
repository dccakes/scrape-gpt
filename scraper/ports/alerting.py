"""
Alerting port - Interface for sending alerts.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from scraper.domain.models import AlertSeverity


class Alerting(ABC):
    """Interface for sending alerts."""

    @abstractmethod
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Send an alert to configured channels.

        Args:
            title: Alert title
            message: Alert message
            severity: Severity level
            metadata: Optional additional data
        """
        pass
