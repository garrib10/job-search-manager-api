from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return the current time in UTC, truncated to whole seconds.

    WHY:
    Endpoints that compare against "now" take this as a FastAPI dependency, so
    each request uses one consistent time and tests can replace it with a
    fixed clock. Seconds are the precision MySQL DATETIME columns store, so
    boundaries such as "exactly 14 days ago" compare cleanly.
    """
    return datetime.now(timezone.utc).replace(microsecond=0)
