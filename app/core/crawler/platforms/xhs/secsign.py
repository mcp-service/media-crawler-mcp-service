# -*- coding: utf-8 -*-
"""Xiaohongshu seccore v2 signing helper (browser-executed).

This uses window.mnsv2 present on the PC web to generate an XYS_ token,
which is then fed into the standard sign() payload as x_s.
"""

from __future__ import annotations

import hashlib
import base64
import json
from typing import Any


def _build_c(e: Any, a: Any) -> str:
    c = str(e)
    if isinstance(a, (dict, list)):
        c += json.dumps(a, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(a, str):
        c += a
    return c


def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


async def seccore_signv2_playwright(page, e: Any, a: Any) -> str:
    """Generate seccore v2 token via page context.

    It requires window.mnsv2(c, d) to be available in the page context.
    Returns an XYS_... string token.
    """
    c = _build_c(e, a)
    d = _md5_hex(c)
    s = await page.evaluate("(payload) => window.mnsv2(payload[0], payload[1])", [c, d])
    f = {
        "x0": "4.2.6",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": s,
        "x4": a,
    }
    payload = json.dumps(f, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = "XYS_" + base64.b64encode(payload).decode("ascii")
    return token


__all__ = ["seccore_signv2_playwright"]

