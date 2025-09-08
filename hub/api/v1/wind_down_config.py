"""Wind-down configuration for NEAR AI Hub service shutdown."""

import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class WindDownConfig:
    """Configuration for the NEAR AI Hub wind-down process."""

    def __init__(self):
        # Wind-down mode - when True, prevents new agent submissions and shows announcements
        self.wind_down_mode = os.getenv("WIND_DOWN_MODE", "false").lower() == "true"

        # Wind-down date - when the service will be shut down
        self.wind_down_date = os.getenv("WIND_DOWN_DATE", "2025-10-01")

        # Grace period for exports after shutdown (in days)
        self.grace_period_days = int(os.getenv("WIND_DOWN_GRACE_PERIOD_DAYS", "30"))

        # Custom announcement message (optional)
        self.announcement_message = os.getenv(
            "WIND_DOWN_MESSAGE",
            f"Important: NEAR AI Hub will be closing on {self.wind_down_date}. "
            "Please export your agents before this date.",
        )

    @property
    def is_wind_down_active(self) -> bool:
        """Check if wind-down mode is currently active."""
        return self.wind_down_mode

    @property
    def shutdown_date(self) -> Optional[datetime]:
        """Get the shutdown date as a datetime object."""
        try:
            return datetime.fromisoformat(self.wind_down_date)
        except (ValueError, AttributeError):
            return None

    @property
    def days_until_shutdown(self) -> Optional[int]:
        """Calculate days remaining until shutdown."""
        if not self.shutdown_date:
            return None

        delta = self.shutdown_date - datetime.now()
        return max(0, delta.days)

    def should_block_uploads(self) -> bool:
        """Determine if new uploads should be blocked."""
        return self.is_wind_down_active

    def should_block_agent_creation(self) -> bool:
        """Determine if new agent creation should be blocked."""
        return self.is_wind_down_active


# Global instance
wind_down_config = WindDownConfig()

