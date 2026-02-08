"""
LocalStorage adapter - Filesystem-based storage for development and testing.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

from scraper.ports.storage import Storage
from scraper.domain.exceptions import StorageError


class LocalStorage(Storage):
    """Local filesystem storage implementation."""

    def __init__(self, base_path: str = "data"):
        """Initialize with base path for all storage."""
        self.base_path = Path(base_path)

    async def save_config(
        self, domain: str, page_type: str, config: Dict[str, Any]
    ) -> str:
        """Save extraction config to local filesystem."""
        config_dir = self.base_path / "configs" / domain
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = config_dir / f"{page_type}.json"

        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2, default=str)
            return str(config_path)
        except Exception as e:
            raise StorageError(f"Failed to save config: {e}")

    async def load_config(
        self, domain: str, page_type: str
    ) -> Optional[Dict[str, Any]]:
        """Load extraction config from local filesystem."""
        config_path = self.base_path / "configs" / domain / f"{page_type}.json"

        if not config_path.exists():
            return None

        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise StorageError(f"Failed to load config: {e}")

    async def save_html(
        self, domain: str, url: str, html: str, timestamp: datetime
    ) -> str:
        """Save raw HTML to local filesystem."""
        html_dir = self.base_path / "html" / domain
        html_dir.mkdir(parents=True, exist_ok=True)

        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        html_path = html_dir / f"{timestamp_str}_{url_hash}.html"

        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            return str(html_path)
        except Exception as e:
            raise StorageError(f"Failed to save HTML: {e}")

    async def save_json(
        self, domain: str, url: str, data: Dict[str, Any], timestamp: datetime
    ) -> str:
        """Save extracted JSON data to local filesystem."""
        json_dir = self.base_path / "json" / domain
        json_dir.mkdir(parents=True, exist_ok=True)

        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        json_path = json_dir / f"{timestamp_str}_{url_hash}.json"

        try:
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return str(json_path)
        except Exception as e:
            raise StorageError(f"Failed to save JSON: {e}")

    async def update_coverage_stats(
        self, domain: str, page_type: str, field_name: str, success: bool
    ) -> None:
        """Update coverage statistics for a field."""
        stats_dir = self.base_path / "coverage-stats" / domain
        stats_dir.mkdir(parents=True, exist_ok=True)

        stats_path = stats_dir / f"{page_type}.json"

        # Load existing stats
        if stats_path.exists():
            with open(stats_path, "r") as f:
                stats = json.load(f)
        else:
            stats = {}

        # Initialize field stats if needed
        if field_name not in stats:
            stats[field_name] = {"successes": 0, "total": 0}

        # Update
        stats[field_name]["total"] += 1
        if success:
            stats[field_name]["successes"] += 1

        # Save
        try:
            with open(stats_path, "w") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to update coverage stats: {e}")

    async def get_coverage_stats(
        self, domain: str, page_type: str
    ) -> Dict[str, float]:
        """Get coverage statistics for a page type."""
        stats_path = (
            self.base_path / "coverage-stats" / domain / f"{page_type}.json"
        )

        if not stats_path.exists():
            return {}

        try:
            with open(stats_path, "r") as f:
                stats = json.load(f)

            # Calculate success rates
            return {
                field: (
                    data["successes"] / data["total"] if data["total"] > 0 else 0.0
                )
                for field, data in stats.items()
            }
        except Exception as e:
            raise StorageError(f"Failed to get coverage stats: {e}")
