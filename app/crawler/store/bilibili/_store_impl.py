# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : persist1@126.com
# @Time    : 2025/9/5 19:34
# @Desc    : B站存储实现类
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict, Optional

import aiofiles

from app.providers.models.bilibili import (
    BilibiliVideo,
    BilibiliVideoComment,
    BilibiliUpInfo,
    BilibiliContactInfo,
    BilibiliUpDynamic,
)
from app.crawler.tools.async_file_writer import AsyncFileWriter
from app.providers.logger import get_logger
from app.crawler.tools.time_util import get_current_timestamp


class BiliCsvStoreImplement:
    def __init__(self):
        # Import contextvars from media_crawler submodule
        import sys
        from pathlib import Path
        media_crawler_path = Path(__file__).parent.parent.parent.parent / "media_crawler"
        if str(media_crawler_path) not in sys.path:
            sys.path.insert(0, str(media_crawler_path))
        from var import crawler_type_var

        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="bilibili"
        )

    async def store_content(self, content_item: Dict):
        """
        content CSV storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=content_item,
            item_type="videos"
        )

    async def store_comment(self, comment_item: Dict):
        """
        comment CSV storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        """
        creator CSV storage implementation
        Args:
            creator:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=creator,
            item_type="creators"
        )

    async def store_contact(self, contact_item: Dict):
        """
        creator contact CSV storage implementation
        Args:
            contact_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=contact_item,
            item_type="contacts"
        )

    async def store_dynamic(self, dynamic_item: Dict):
        """
        creator dynamic CSV storage implementation
        Args:
            dynamic_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=dynamic_item,
            item_type="dynamics"
        )


class BiliDbStoreImplement:
    """
    B站数据库存储实现类 - 使用 Tortoise ORM
    按照 Rule 7: Tortoise ORM Usage for Database Operations
    """

    async def store_content(self, content_item: Dict):
        """
        Bilibili content DB storage implementation using Tortoise ORM
        Args:
            content_item: content item dict
        """
        video_id = content_item.get("video_id")

        # Try to get existing video
        video = await BilibiliVideo.filter(video_id=video_id).first()

        if video:
            # Update existing video
            for key, value in content_item.items():
                setattr(video, key, value)
            video.last_modify_ts = get_current_timestamp()
            await video.save()
        else:
            # Create new video
            content_item["add_ts"] = get_current_timestamp()
            content_item["last_modify_ts"] = get_current_timestamp()
            await BilibiliVideo.create(**content_item)

    async def store_comment(self, comment_item: Dict):
        """
        Bilibili comment DB storage implementation using Tortoise ORM
        Args:
            comment_item: comment item dict
        """
        comment_id = comment_item.get("comment_id")

        # Try to get existing comment
        comment = await BilibiliVideoComment.filter(comment_id=comment_id).first()

        if comment:
            # Update existing comment
            for key, value in comment_item.items():
                setattr(comment, key, value)
            comment.last_modify_ts = get_current_timestamp()
            await comment.save()
        else:
            # Create new comment
            comment_item["add_ts"] = get_current_timestamp()
            comment_item["last_modify_ts"] = get_current_timestamp()
            await BilibiliVideoComment.create(**comment_item)

    async def store_creator(self, creator: Dict):
        """
        Bilibili creator DB storage implementation using Tortoise ORM
        Args:
            creator: creator item dict
        """
        user_id = creator.get("user_id")

        # Try to get existing creator
        up_info = await BilibiliUpInfo.filter(user_id=user_id).first()

        if up_info:
            # Update existing creator
            for key, value in creator.items():
                setattr(up_info, key, value)
            up_info.last_modify_ts = get_current_timestamp()
            await up_info.save()
        else:
            # Create new creator
            creator["add_ts"] = get_current_timestamp()
            creator["last_modify_ts"] = get_current_timestamp()
            await BilibiliUpInfo.create(**creator)

    async def store_contact(self, contact_item: Dict):
        """
        Bilibili contact DB storage implementation using Tortoise ORM
        Args:
            contact_item: contact item dict
        """
        up_id = contact_item.get("up_id")
        fan_id = contact_item.get("fan_id")

        # Try to get existing contact
        contact = await BilibiliContactInfo.filter(up_id=up_id, fan_id=fan_id).first()

        if contact:
            # Update existing contact
            for key, value in contact_item.items():
                setattr(contact, key, value)
            contact.last_modify_ts = get_current_timestamp()
            await contact.save()
        else:
            # Create new contact
            contact_item["add_ts"] = get_current_timestamp()
            contact_item["last_modify_ts"] = get_current_timestamp()
            await BilibiliContactInfo.create(**contact_item)

    async def store_dynamic(self, dynamic_item: Dict):
        """
        Bilibili dynamic DB storage implementation using Tortoise ORM
        Args:
            dynamic_item: dynamic item dict
        """
        dynamic_id = dynamic_item.get("dynamic_id")

        # Try to get existing dynamic
        dynamic = await BilibiliUpDynamic.filter(dynamic_id=dynamic_id).first()

        if dynamic:
            # Update existing dynamic
            for key, value in dynamic_item.items():
                setattr(dynamic, key, value)
            dynamic.last_modify_ts = get_current_timestamp()
            await dynamic.save()
        else:
            # Create new dynamic
            dynamic_item["add_ts"] = get_current_timestamp()
            dynamic_item["last_modify_ts"] = get_current_timestamp()
            await BilibiliUpDynamic.create(**dynamic_item)


class BiliJsonStoreImplement:
    def __init__(self):
        # Import contextvars from media_crawler submodule
        import sys
        from pathlib import Path
        media_crawler_path = Path(__file__).parent.parent.parent.parent / "media_crawler"
        if str(media_crawler_path) not in sys.path:
            sys.path.insert(0, str(media_crawler_path))
        from var import crawler_type_var

        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="bilibili"
        )

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        """
        creator JSON storage implementation
        Args:
            creator:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=creator,
            item_type="creators"
        )

    async def store_contact(self, contact_item: Dict):
        """
        creator contact JSON storage implementation
        Args:
            contact_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=contact_item,
            item_type="contacts"
        )

    async def store_dynamic(self, dynamic_item: Dict):
        """
        creator dynamic JSON storage implementation
        Args:
            dynamic_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=dynamic_item,
            item_type="dynamics"
        )



