# -*- coding: utf-8 -*-
"""Proxy provider factories."""

from .kuaidl_proxy import new_kuai_daili_proxy  # noqa: F401
from .wandou_http_proxy import new_wandou_http_proxy  # noqa: F401

__all__ = ["new_kuai_daili_proxy", "new_wandou_http_proxy"]
