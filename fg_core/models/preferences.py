"""Persisted household preferences for FamilyGuild Core."""

from dataclasses import dataclass, field

import dbzero as db0


@db0.memo(id="/familyguild/core/CorePreferences")
@dataclass
class CorePreferences:
    """Persisted foundation preferences for the one-household app state."""

    family_display_name: str = "Family"
    currency_name: str = "FamCoins"
    language_preference: str = "en"
    ui_preferences: dict[str, object] = field(default_factory=dict)
