# -*- coding: utf-8 -*-
"""Crawler platform base exports."""

from app.core.crawler.platforms.base import (  # noqa: F401
    AbstractCrawler,
    AbstractLogin,
    AbstractStore,
)

__all__ = [
    "AbstractCrawler",
    "AbstractLogin",
    "AbstractStore",
]
