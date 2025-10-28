# -*- coding: utf-8 -*-
"""Helper utilities for Xiaohongshu crawler."""

from __future__ import annotations

import ctypes
import json
import random
import time
import urllib.parse
from typing import Dict, Iterable

from app.core.crawler.model.m_xiaohongshu import CreatorUrlInfo, NoteUrlInfo
from app.core.crawler.tools import crawler_util


def parse_note_info_from_note_url(url: str) -> NoteUrlInfo:
    """Parse note information from a Xiaohongshu note URL."""
    if not url:
        raise ValueError("note url 不能为空")
    
    try:
        normalized = normalize_url(url)
        path_parts = normalized.split("/")
        if len(path_parts) < 2:
            raise ValueError(f"Invalid note URL format: {url}")
        note_id = path_parts[-1].split("?")[0]
        if not note_id:
            raise ValueError(f"Cannot extract note_id from URL: {url}")
        
        params = crawler_util.extract_url_params_to_dict(normalized)
        return NoteUrlInfo(
            note_id=note_id,
            xsec_token=params.get("xsec_token", ""),
            xsec_source=params.get("xsec_source", ""),
        )
    except (IndexError, AttributeError) as e:
        raise ValueError(f"Failed to parse note URL {url}: {e}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """Parse creator information from profile URL or plain user id."""
    if not url:
        raise ValueError("creator url 不能为空")

    stripped = url.strip()
    
    # If it's a simple string (user_id), use it directly
    # This matches the original MediaCrawler behavior where user_id is passed directly
    if not stripped.startswith(("http://", "https://", "/")):
        return CreatorUrlInfo(user_id=stripped, xsec_token="", xsec_source="")
    
    # Plain user id (24 hex characters) is also accepted.
    if len(stripped) == 24 and all(c in "0123456789abcdef" for c in stripped):
        return CreatorUrlInfo(user_id=stripped, xsec_token="", xsec_source="")

    try:
        normalized = normalize_url(stripped)
        user_segment = "/user/profile/"
        if user_segment not in normalized:
            raise ValueError(f"URL does not contain expected user profile path: {url}")

        parts = normalized.split(user_segment, 1)
        if len(parts) < 2:
            raise ValueError(f"Cannot split URL by user profile path: {url}")
            
        user_id = parts[-1].split("?")[0]
        if not user_id:
            raise ValueError(f"Cannot extract user_id from URL: {url}")
            
        params = crawler_util.extract_url_params_to_dict(normalized)
        return CreatorUrlInfo(
            user_id=user_id,
            xsec_token=params.get("xsec_token", ""),
            xsec_source=params.get("xsec_source", ""),
        )
    except (IndexError, AttributeError) as e:
        raise ValueError(f"Failed to parse creator URL {url}: {e}")


def normalize_url(url: str) -> str:
    """Ensure URL contains scheme and host."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme:
        return url
    return urllib.parse.urlunsplit(
        ("https", "www.xiaohongshu.com", parsed.path, parsed.query, parsed.fragment)
    )


def get_search_id() -> str:
    """Generate search id compatible with Xiaohongshu search API."""
    epoch_ms = int(time.time() * 1000) << 64
    entropy = int(random.uniform(0, 2147483646))
    return base36encode(epoch_ms + entropy)


def base36encode(number: int, alphabet: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") -> str:
    """Convert integer to base36 string."""
    if number == 0:
        return alphabet[0]
    negative = number < 0
    number = abs(number)
    digits = []
    while number:
        number, idx = divmod(number, len(alphabet))
        digits.append(alphabet[idx])
    if negative:
        digits.append("-")
    return "".join(reversed(digits))


def sign(a1: str = "", b1: str = "", x_s: str = "", x_t: str = "") -> Dict[str, str]:
    """Generate signature headers compatible with Xiaohongshu web API."""
    payload = {
        "s0": 3,
        "s1": "",
        "x0": "1",
        "x1": "4.2.2",
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.74.0",
        "x5": a1,
        "x6": x_t,
        "x7": x_s,
        "x8": b1,
        "x9": _mrc(x_t + x_s + b1),
        "x10": 154,
        "x11": "normal",
    }
    encoded = _encode_utf8(json.dumps(payload, separators=(",", ":")))
    x_s_common = _b64encode(encoded)
    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": x_s_common,
        "x-b3-traceid": _get_b3_trace_id(),
    }


def _get_b3_trace_id() -> str:
    chars = "abcdef0123456789"
    return "".join(random.choice(chars) for _ in range(16))


def _encode_utf8(text: str) -> Iterable[int]:
    result: list[int] = []
    for char in text:
        code = ord(char)
        if code < 0x80:
            result.append(code)
        elif code < 0x800:
            result.extend((0xC0 | (code >> 6), 0x80 | (code & 0x3F)))
        elif 0xD800 <= code <= 0xDBFF:
            # surrogate pair
            continue
        else:
            result.extend(
                (
                    0xE0 | (code >> 12),
                    0x80 | ((code >> 6) & 0x3F),
                    0x80 | (code & 0x3F),
                )
            )
    return result


def _b64encode(data: Iterable[int]) -> str:
    import base64

    return base64.b64encode(bytes(data)).decode("ascii")


def _mrc(value: str) -> str:
    """Compute CRC32 for given string using a 256-entry table.

    The previous implementation embedded a truncated table (250 entries),
    which caused intermittent IndexError: list index out of range when the
    index landed in 250..255. Here we generate the standard 256-entry table
    once and use it to compute the checksum, matching the previous algorithm
    (initial 0xFFFFFFFF, final XOR 0xFFFFFFFF).
    """

    # Build table lazily and cache on the function
    table = getattr(_mrc, "_table", None)
    if table is None:
        poly = 0xEDB88320
        table = []
        for i in range(256):
            c = i
            for _ in range(8):
                if c & 1:
                    c = poly ^ (c >> 1)
                else:
                    c >>= 1
            table.append(c)
        setattr(_mrc, "_table", table)

    crc = 0xFFFFFFFF
    for ch in value:
        crc = table[(crc ^ ord(ch)) & 0xFF] ^ (crc >> 8)
    crc ^= 0xFFFFFFFF
    return hex(ctypes.c_uint32(crc).value)[2:]


__all__ = [
    "parse_note_info_from_note_url",
    "parse_creator_info_from_url",
    "normalize_url",
    "get_search_id",
    "sign",
]
