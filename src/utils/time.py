from __future__ import annotations
import re, time, datetime as dt

def parse_since_to_timestamp(since: str, now_ts: int | None = None) -> int:
    """Accepts ISO date (YYYY-MM-DD) or ISO8601 period like P7D, P1M."""
    now_ts = now_ts or int(time.time())
    if not since:
        return 0
    # date
    try:
        t = dt.datetime.strptime(since, "%Y-%m-%d")
        return int(t.timestamp())
    except Exception:
        pass
    # period like P7D, P1M
    m = re.fullmatch(r"P(?:(\d+)D)?(?:(\d+)M)?(?:(\d+)Y)?", since)
    if m:
        days = int(m.group(1) or 0) + (int(m.group(2) or 0) * 30) + (int(m.group(3) or 0) * 365)
        return now_ts - days * 86400
    return 0
