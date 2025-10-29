import pathlib
from typing import Dict

import aiofiles
from app.providers.logger import get_logger


class BilibiliVideo:
    # 统一使用平台代号目录，避免与 'bili' 重复
    video_store_path: str = "data/bili/videos"

    async def store_video(self, video_content_item: Dict):
        """
        store content
        
        Args:
            video_content_item:

        Returns:

        """
        await self.save_video(video_content_item.get("aid"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"))

    def make_save_file_name(self, aid: str, extension_file_name: str) -> str:
        """
        make save file name by store type
        
        Args:
            aid: aid
            extension_file_name: video filename with extension
            
        Returns:

        """
        return f"{self.video_store_path}/{aid}/{extension_file_name}"

    async def save_video(self, aid: int, video_content: str, extension_file_name="mp4"):
        """
        save video to local
        
        Args:
            aid: aid
            video_content: video content
            extension_file_name: video filename with extension

        Returns:

        """
        pathlib.Path(self.video_store_path + "/" + str(aid)).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(str(aid), extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(video_content)
            get_logger().info(f"[BilibiliVideoImplement.save_video] save save_video {save_file_name} success ...")
