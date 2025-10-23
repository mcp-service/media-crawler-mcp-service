# -*- coding: utf-8 -*-
"""Fallback HTML extractor for Xiaohongshu note detail."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Dict, Optional

from app.providers.logger import get_logger

logger = get_logger()


class XiaoHongShuExtractor:
    """Utility to extract note detail from rendered HTML when API fails."""

    # 支持两种形态：
    # 1) 直接对象: window.__INITIAL_STATE__ = {...}</script>
    # 2) 编码字符串: window.__INITIAL_STATE__ = JSON.parse(decodeURIComponent("..."))</script>
    _pattern_obj = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.DOTALL)
    _pattern_dc = re.compile(r"window\.__INITIAL_STATE__\s*=\s*JSON\.parse\(decodeURIComponent\(\"(.*?)\"\)\)\s*</script>", re.DOTALL)

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        if not html:
            return None

        state = self._extract_state(html)
        if not state:
            return None

        try:
            return (
                state.get("note", {})
                .get("noteDetailMap", {})
                .get(note_id, {})
                .get("note")
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("[xhs.extractor] parse note detail failed: %s", exc)
            return None

    def extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        state = self._extract_state(html)
        if not state:
            return None
        return state.get("user", {}).get("userPageData")

    def _extract_state(self, html: str) -> Optional[Dict]:
        text = html or ""
        # 直接对象形式
        m1 = self._pattern_obj.search(text)
        if m1:
            payload = m1.group(1)
            try:
                sanitized = payload.replace(":undefined", ":null")
                return json.loads(sanitized)
            except json.JSONDecodeError as exc:
                logger.debug("[xhs.extractor] parse json failed: %s", exc)
                return None

        # JSON.parse(decodeURIComponent()) 形式
        m2 = self._pattern_dc.search(text)
        if m2:
            encoded = m2.group(1)
            try:
                decoded = urllib.parse.unquote(encoded)
                sanitized = decoded.replace(":undefined", ":null")
                return json.loads(sanitized)
            except Exception as exc:
                logger.debug("[xhs.extractor] parse decode json failed: %s", exc)
                return None

        logger.debug("[xhs.extractor] initial state not found")
        return None


__all__ = ["XiaoHongShuExtractor"]
