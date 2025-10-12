# -*- coding: utf-8 -*-
"""
Database configuration bridge for MediaCrawler
将主项目的数据库配置同步到MediaCrawler
"""
import os
from pathlib import Path


def sync_db_config_to_media_crawler() -> None:
    """
    同步数据库配置到MediaCrawler的db_config.py

    从主项目的环境变量读取数据库配置，并写入到media_crawler的配置文件
    """
    # 读取主项目环境变量
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_name = os.getenv("DB_NAME", "mcp_tools_db")

    # MediaCrawler配置文件路径
    media_crawler_path = Path(__file__).parent.parent.parent.parent / "media_crawler"
    db_config_path = media_crawler_path / "config" / "db_config.py"

    if not db_config_path.exists():
        print(f"警告: MediaCrawler配置文件不存在: {db_config_path}")
        return

    # 构建配置内容 (覆盖MediaCrawler的db_config.py中的变量)
    config_override = f'''
# 此配置由主项目自动同步，请勿手动修改
# 数据库配置 - 与主项目共享
RELATION_DB_PWD = "{db_password}"
RELATION_DB_HOST = "{db_host}"
RELATION_DB_PORT = "{db_port}"
RELATION_DB_USER = "{db_user}"
RELATION_DB_NAME = "{db_name}"
'''

    try:
        # 读取原配置文件
        with open(db_config_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 检查是否已经有自动同步标记
        if "# 此配置由主项目自动同步" in original_content:
            # 如果已存在，替换同步部分
            lines = original_content.split("\n")
            new_lines = []
            skip = False

            for line in lines:
                if "# 此配置由主项目自动同步" in line:
                    skip = True
                    continue
                if skip and line.strip() and not line.startswith("#") and not line.startswith("RELATION_DB"):
                    skip = False

                if not skip:
                    new_lines.append(line)

            # 添加新的配置
            final_content = "\n".join(new_lines) + "\n" + config_override
        else:
            # 如果不存在，追加到文件末尾
            final_content = original_content + "\n" + config_override

        # 写回配置文件
        with open(db_config_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"✅ 数据库配置已同步到MediaCrawler: {db_config_path}")

    except Exception as e:
        print(f"❌ 同步数据库配置失败: {e}")


# 模块导入时自动执行同步
if __name__ != "__main__":
    sync_db_config_to_media_crawler()