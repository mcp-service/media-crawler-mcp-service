# -*- coding: utf-8 -*-
"""Enum definitions for Xiaohongshu crawler."""

from enum import Enum


class SearchSortType(str, Enum):
    """Supported search sort orders."""

    GENERAL = "general"
    HOT = "hot"
    LATEST = "time"
    RELEVANCE = "sim"


class SearchNoteType(str, Enum):
    """Supported note type filters."""

    ALL = "all"
    VIDEO = "video"
    IMAGE = "image"
