# -*- coding: utf-8 -*-
"""
Platform endpoints package
"""
from .xiaohongshu import XiaohongshuEndpoint
from .douyin import DouyinEndpoint
from .kuaishou import KuaishouEndpoint
from .bilibili import BilibiliEndpoint
from .weibo import WeiboEndpoint
from .tieba import TiebaEndpoint
from .zhihu import ZhihuEndpoint

__all__ = [
    "XiaohongshuEndpoint",
    "DouyinEndpoint",
    "KuaishouEndpoint",
    "BilibiliEndpoint",
    "WeiboEndpoint",
    "TiebaEndpoint",
    "ZhihuEndpoint",
]