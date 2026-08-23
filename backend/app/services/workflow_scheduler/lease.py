from __future__ import annotations

from datetime import datetime

from .time import normalize_utc


def lease_available(now: datetime, lease_expires_at: datetime | None) -> bool:
    """判断调度槽位是否允许被当前 worker 抢占。"""
    now_utc = normalize_utc(now)
    if lease_expires_at is None:
        return True
    return normalize_utc(lease_expires_at) <= now_utc
