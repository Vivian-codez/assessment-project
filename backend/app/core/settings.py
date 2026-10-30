"""Alias export for app.core.config.settings."""

# Import the settings singleton and Settings class definition from app.core.config
from app.core.config import settings, Settings

# Export settings and Settings for external consumers importing from app.core.settings
__all__ = ["settings", "Settings"]
