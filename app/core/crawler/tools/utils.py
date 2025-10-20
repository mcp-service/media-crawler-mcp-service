# -*- coding: utf-8 -*-
"""Utility helpers for crawler modules."""

from __future__ import annotations

import time
from datetime import datetime

from app.providers.logger import get_logger


logger = get_logger()


def get_unix_timestamp() -> int:
    """Return current Unix timestamp (seconds)."""
    return int(time.time())


def get_unix_time_from_time_str(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
    """Convert time string to Unix timestamp."""
    try:
        return int(datetime.strptime(time_str, fmt).timestamp())
    except Exception:
        logger.warning(
            f"[utils.get_unix_time_from_time_str] invalid time string: {time_str}"
        )
        return get_unix_timestamp()
