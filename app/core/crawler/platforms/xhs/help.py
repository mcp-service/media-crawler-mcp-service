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
        "x1": "3.7.8-2",
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.27.2",
        "x5": a1,
        "x6": x_t,
        "x7": x_s,
        "x8": b1,
        "x9": _mrc(x_t + x_s + b1),
        "x10": 154,
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
    table = [
        0,
        1996959894,
        3993919788,
        2567524794,
        124634137,
        1886057615,
        3915621685,
        2657392035,
        249268274,
        2044508324,
        3772115230,
        2547177864,
        162941995,
        2125561021,
        3887607047,
        2428444049,
        498536548,
        1789927666,
        4089016648,
        2227061214,
        450548861,
        1843258603,
        4107580753,
        2211677639,
        325883990,
        1684777152,
        4251122042,
        2321926636,
        335633487,
        1661365465,
        4195302755,
        2366115317,
        997073096,
        1281953886,
        3579855332,
        2724688242,
        1006888145,
        1258607687,
        3524101629,
        2768942443,
        901097722,
        1119000684,
        3686517206,
        2898065728,
        853044451,
        1172266101,
        3705015759,
        2882616665,
        651767980,
        1373503546,
        3369554304,
        3218104598,
        565507253,
        1454621731,
        3485111705,
        3099436303,
        671266974,
        1594198024,
        3322730930,
        2970347812,
        795835527,
        1483230225,
        3244367275,
        3060149565,
        1994146192,
        31158534,
        2563907772,
        4023717930,
        1907459465,
        112637215,
        2680153253,
        3904427059,
        2013776290,
        251722036,
        2517215374,
        3775830040,
        2137656763,
        141376813,
        2439277719,
        3865271297,
        1802195444,
        476864866,
        2238001368,
        4066508878,
        1812370925,
        453092731,
        2181625025,
        4111451223,
        1706088902,
        314042704,
        2344532202,
        4240017532,
        1658658271,
        366619977,
        2362670323,
        4224994405,
        1303535960,
        984961486,
        2747007092,
        3569037538,
        1256170817,
        1037604311,
        2765210733,
        3554079995,
        1131014506,
        879679996,
        2909243462,
        3663771856,
        1141124467,
        855842277,
        2852801631,
        3708648649,
        1342533948,
        654459306,
        3188396048,
        3373015174,
        1466479909,
        544179635,
        3110523913,
        3462522015,
        1591671054,
        702138776,
        2966460450,
        3352799412,
        1504918807,
        783551873,
        3082640443,
        3233442989,
        3988292384,
        2596254646,
        62317068,
        1957810842,
        3939845945,
        2647816111,
        81470997,
        1943803523,
        3814918930,
        2489596804,
        225274430,
        2053790376,
        3826175755,
        2466906013,
        167816743,
        2097651377,
        4027552580,
        2265490386,
        503444072,
        1762050814,
        4150417245,
        2154129355,
        426522225,
        1852507879,
        4275313526,
        2312317920,
        282753626,
        1742555852,
        4189708143,
        2394877945,
        397917763,
        1622183637,
        3604390888,
        2714866558,
        953729732,
        1340076626,
        3518719985,
        2797360999,
        1068828381,
        1219638859,
        3624741850,
        2936675148,
        906185462,
        1090812512,
        3747672003,
        2825379669,
        829329135,
        1181335161,
        3412177804,
        3160834842,
        628085408,
        1382605366,
        3423369109,
        3138078467,
        570562233,
        1426400815,
        3317316542,
        2998733608,
        733239954,
        1555261956,
        3268935591,
        3050360625,
        752459403,
        1541320221,
        2607071920,
        3965973030,
        1969922972,
        40735498,
        2617837225,
        3943577151,
        1913087877,
        83908371,
        2512341634,
        3803740692,
        2075208622,
        213261112,
        2463272603,
        3855990285,
        2094854071,
        198958881,
        2262029012,
        4057260610,
        1759359992,
        534414190,
        2176718541,
        4139329115,
        1873836001,
        414664567,
        2282248934,
        4279200368,
        1711684554,
        285281116,
        2405801727,
        4167216745,
        1634467795,
        376229701,
        2685067896,
        3608007406,
        1308918612,
        956543938,
        2808555105,
        3495958263,
        1231636301,
        1047427035,
        2932959818,
        3654703836,
        1088359270,
        936918000,
        2847714899,
        3736837829,
        1202900863,
        817233897,
        3183342108,
        3401237130,
        1404277552,
        615818150,
        3134207493,
        3453421203,
        1423857449,
        591330540,
        3244367275,
        3060149565,
    ]

    crc = -1
    for char in value:
        crc = table[(crc ^ ord(char)) & 0xFF] ^ (crc >> 8)
    return hex(ctypes.c_uint32(crc ^ -1).value)[2:]


__all__ = [
    "parse_note_info_from_note_url",
    "parse_creator_info_from_url",
    "normalize_url",
    "get_search_id",
    "sign",
]
