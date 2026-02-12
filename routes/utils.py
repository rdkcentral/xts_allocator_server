"""Shared utility functions for route handlers."""

from datetime import timezone


def ensure_utc(dt):
    """Make a datetime timezone-aware (UTC) if it is naive.

    SQLite strips timezone info from stored datetimes, so values read back
    are naive.  This helper re-attaches UTC so they can be compared with
    timezone-aware ``datetime.now(timezone.utc)`` values.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_target_id(device):
    """Build a stable allocation target identifier for a device."""
    rack_name = device.rack.name if device.rack else f"rack-{device.rack_id}"
    platform = device.platform or "unknown"
    return f"{platform}@{rack_name}/{device.slot_name}"


def normalize_tags(raw_tags):
    """Normalize tags/labels input to comma-separated lowercase string."""
    if raw_tags is None:
        return ""
    if isinstance(raw_tags, list):
        items = [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]
    else:
        items = [item.strip().lower() for item in str(raw_tags).split(",") if item.strip()]
    # Preserve order while removing duplicates.
    return ",".join(dict.fromkeys(items))
