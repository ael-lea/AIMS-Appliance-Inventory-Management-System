"""Application-wide constants: theme colours, paths and tax settings.

Keeping every constant here means a colour or the VAT rate is changed in
exactly one place.
"""
import os

# The folder that contains cashier_dashboard.py, session.py, auth.py and icons/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Theme:
    """Colour palette used by every page (same look as the Admin dashboard)."""

    NAVY = "#012148"
    ACTIVE = "#053e87"
    BG = "#FDFCF8"
    CARD = "#FFFFFF"
    TEXT = "#202833"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    GREEN = "#1E8449"
    ORANGE = "#B9770E"
    CARD_GRAY = "#B2B4B7"      # the big summary cards
    LIGHT_BTN = "#E9EEF5"      # light (secondary) buttons
    LIGHT_ACTIVE = "#DCE4EE"   # light buttons while the mouse is over them
    DANGER = "#B42318"         # red text for Remove / Clear
    DISABLED_BG = "#9AA7B8"    # Confirm Order while it is not ready
    ENTRY_BORDER = "#C3CCDA"   # outline of the rounded text boxes


class Settings:
    """Business and file-system settings."""

    ICON_DIR = os.path.join(PROJECT_ROOT, "photos")
    VAT_RATE = 0.12              # Prices are VAT-inclusive. Use 0 to hide VAT.
    WALK_IN_CUSTOMER = "Walk-in Customer"
    LOW_STOCK_LEVEL = 10         # stock at or below this is shown in orange
