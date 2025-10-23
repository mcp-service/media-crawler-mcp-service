# -*- coding: utf-8 -*-
"""Platform specific exceptions for Xiaohongshu."""


class DataFetchError(RuntimeError):
    """Raised when an API call succeeds but returns an error payload."""


class IPBlockError(RuntimeError):
    """Raised when the platform actively blocks the IP."""
