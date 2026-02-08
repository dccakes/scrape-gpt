"""
Unit tests for ConsoleAlerting adapter.
"""

import pytest
from scraper.domain.models import AlertSeverity
from scraper.adapters.alerting.console_alerting import ConsoleAlerting


@pytest.mark.unit
@pytest.mark.asyncio
async def test_console_alerting_sends_info_alert(capsys):
    """GIVEN ConsoleAlerting adapter, WHEN sending INFO alert, THEN prints with ℹ️ emoji."""
    alerting = ConsoleAlerting()

    await alerting.send_alert(
        title="Test Info",
        message="This is an info message",
        severity=AlertSeverity.INFO,
    )

    captured = capsys.readouterr()
    assert "ℹ️" in captured.out
    assert "[INFO]" in captured.out
    assert "Test Info" in captured.out
    assert "This is an info message" in captured.out


@pytest.mark.unit
@pytest.mark.asyncio
async def test_console_alerting_sends_warning_alert(capsys):
    """GIVEN ConsoleAlerting adapter, WHEN sending WARNING alert, THEN prints with ⚠️ emoji."""
    alerting = ConsoleAlerting()

    await alerting.send_alert(
        title="Test Warning",
        message="This is a warning",
        severity=AlertSeverity.WARNING,
    )

    captured = capsys.readouterr()
    assert "⚠️" in captured.out
    assert "[WARNING]" in captured.out
    assert "Test Warning" in captured.out


@pytest.mark.unit
@pytest.mark.asyncio
async def test_console_alerting_sends_critical_alert(capsys):
    """GIVEN ConsoleAlerting adapter, WHEN sending CRITICAL alert, THEN prints with 🚨 emoji."""
    alerting = ConsoleAlerting()

    await alerting.send_alert(
        title="Test Critical",
        message="This is critical",
        severity=AlertSeverity.CRITICAL,
    )

    captured = capsys.readouterr()
    assert "🚨" in captured.out
    assert "[CRITICAL]" in captured.out
    assert "Test Critical" in captured.out


@pytest.mark.unit
@pytest.mark.asyncio
async def test_console_alerting_includes_metadata(capsys):
    """GIVEN ConsoleAlerting with metadata, WHEN sending alert, THEN metadata is printed."""
    alerting = ConsoleAlerting()

    await alerting.send_alert(
        title="Test",
        message="Message",
        severity=AlertSeverity.INFO,
        metadata={"domain": "example.com", "page_type": "team_page"},
    )

    captured = capsys.readouterr()
    assert "Metadata:" in captured.out
    assert "domain" in captured.out
    assert "example.com" in captured.out
