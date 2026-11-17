"""Tracking number generator for shipments."""
import secrets
from datetime import datetime

# No 0/O or 1/I, so numbers are easy to read out or type from a printed label.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_tracking_number():
    """Return a tracking number like 'TRK-20261110-7K2M9QXD'.

    The date part makes numbers easy to place in time; the 8 random characters
    (32^8, about 1.1 trillion combinations per day) make a repeat practically
    impossible, even when many are generated in the same second.
    """
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"TRK-{date_part}-{random_part}"
