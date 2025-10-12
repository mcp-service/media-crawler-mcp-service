# -*- coding: utf-8 -*-
"""
MCP Prompt Templates - 提供预定义的提示词模板
"""
from typing import Dict, List
from fastmcp import FastMCP
from app.providers.logger import get_logger


def register_prompts(app: FastMCP) -> None:
    """注册所有MCP提示词模板"""

    # 通用爬虫提示词
    @app.prompt()
    async def crawler_basic() -> str:
        """
        基础爬虫使用指南

        这个提示词模板提供了如何使用社交媒体爬虫工具的基本说明
        """
        return """# 社交媒体爬虫工具使用指南

## 支持的平台
- 小红书 (xhs)
- 抖音 (dy)
- 快手 (ks)
- B站 (bili)
- 微博 (wb)
- 贴吧 (tieba)
- 知乎 (zhihu)

## 基础使用流程

### 1. 关键词搜索爬取
使用 `{platform}_search` 工具搜索并爬取内容：
- keywords: 搜索关键词
- max_notes: 最大爬取数量
- enable_comments: 是否爬取评论

### 2. 指定内容爬取
使用 `{platform}_detail` 工具爬取指定URL的内容：
- urls: 内容URL列表
- enable_comments: 是否爬取评论

### 3. 创作者主页爬取
使用 `{platform}_creator` 工具爬取创作者的所有内容：
- creator_ids: 创作者ID列表
- enable_comments: 是否爬取评论

## 注意事项
1. 请遵守平台使用条款和robots.txt规则
2. 合理控制请求频率，避免给平台带来负担
3. 仅用于学习和研究目的，不得用于商业用途
4. 数据默认保存在 data/ 目录下
"""

    # 小红书专用提示词
    @app.prompt()
    async def xiaohongshu_guide() -> str:
        """
        小红书爬虫使用指南

        专门针对小红书平台的爬虫使用说明和最佳实践
        """
        return """# 小红书爬虫使用指南

## 工具列表
- `xhs_search`: 关键词搜索
- `xhs_detail`: 指定笔记爬取
- `xhs_creator`: 创作者主页爬取

## 使用示例

### 搜索美妆相关笔记
```json
{
  "keywords": "美妆教程,化妆技巧",
  "max_notes": 20,
  "enable_comments": true,
  "max_comments_per_note": 10,
  "login_type": "qrcode"
}
```

### 爬取指定笔记
```json
{
  "urls": [
    "https://www.xiaohongshu.com/explore/xxx",
    "https://www.xiaohongshu.com/explore/yyy"
  ],
  "enable_comments": true
}
```

### 爬取创作者主页
```json
{
  "creator_ids": ["user_id_1", "user_id_2"],
  "enable_comments": true,
  "max_comments_per_note": 10
}
```

## 登录方式
- qrcode: 扫码登录（推荐）
- phone: 手机号登录
- cookie: Cookie登录

## 数据保存
- json: JSON文件（默认）
- csv: CSV文件
- db: MySQL数据库
- sqlite: SQLite数据库

## 最佳实践
1. 首次使用建议使用扫码登录
2. max_notes设置为20的倍数效果最佳
3. 开启评论爬取会显著增加时间
4. 建议在非高峰时段爬取
"""

    # 数据分析提示词
    @app.prompt()
    async def data_analysis() -> str:
        """
        爬取数据分析指南

        提供如何分析爬取到的社交媒体数据的指导
        """
        return """# 社交媒体数据分析指南

## 数据文件位置
爬取的数据默认保存在 `data/` 目录下，按照平台和时间组织：
```
data/
├── xhs/
│   ├── notes_YYYYMMDD.json
│   └── comments_YYYYMMDD.json
├── dy/
│   └── videos_YYYYMMDD.json
...
```

## JSON数据结构

### 笔记/帖子数据
```json
{
  "note_id": "笔记ID",
  "title": "标题",
  "desc": "描述",
  "author": {
    "user_id": "用户ID",
    "nickname": "昵称"
  },
  "interact_info": {
    "liked_count": "点赞数",
    "collected_count": "收藏数",
    "comment_count": "评论数"
  },
  "tags": ["标签1", "标签2"],
  "image_list": [...],
  "create_time": "发布时间"
}
```

### 评论数据
```json
{
  "comment_id": "评论ID",
  "note_id": "所属笔记ID",
  "content": "评论内容",
  "user_info": {
    "user_id": "用户ID",
    "nickname": "昵称"
  },
  "like_count": "点赞数",
  "sub_comment_count": "子评论数",
  "create_time": "评论时间"
}
```

## 分析建议

### 1. 内容热度分析
- 统计点赞、收藏、评论等互动数据
- 分析热门标签和关键词
- 识别高互动内容特征

### 2. 时间趋势分析
- 按时间维度统计发布数量
- 分析最佳发布时间
- 追踪话题热度变化

### 3. 用户行为分析
- 创作者粉丝互动率
- 评论情感分析
- 用户画像构建

### 4. 内容质量评估
- 图文质量分析
- 标题吸引力评分
- 内容相关性计算

## 使用Python分析示例
```python
import json
import pandas as pd

# 读取数据
with open('data/xhs/notes_20240101.json', 'r', encoding='utf-8') as f:
    notes = json.load(f)

# 转换为DataFrame
df = pd.DataFrame(notes)

# 计算平均互动数
avg_likes = df['interact_info'].apply(lambda x: x['liked_count']).mean()
print(f"平均点赞数: {avg_likes}")

# 热门标签统计
all_tags = []
for tags in df['tags']:
    all_tags.extend(tags)
tag_counts = pd.Series(all_tags).value_counts()
print("热门标签TOP10:")
print(tag_counts.head(10))
```
"""

    # 故障排查提示词
    @app.prompt()
    async def troubleshooting() -> str:
        """
        故障排查指南

        提供常见问题的解决方案
        """
        return """# 爬虫故障排查指南

## 常见问题及解决方案

### 1. 登录失败
**问题**: 二维码扫描后无法登录
**解决方案**:
- 确保使用headless=false以便手动处理验证
- 检查网络连接
- 尝试使用cookie登录方式
- 清除browser_data目录重试

### 2. 爬取失败
**问题**: 工具调用后返回错误
**解决方案**:
- 检查平台是否更新了接口
- 验证登录态是否有效
- 降低max_notes数量重试
- 检查IP是否被限制

### 3. 数据不完整
**问题**: 爬取的数据字段缺失
**解决方案**:
- 检查目标内容是否存在
- 验证URL格式是否正确
- 尝试增加爬取间隔时间
- 检查日志文件获取详细错误信息

### 4. 性能问题
**问题**: 爬取速度过慢
**解决方案**:
- 禁用评论爬取（enable_comments=false）
- 减少max_comments_per_note数量
- 使用sqlite代替json保存
- 降低并发数量

### 5. Docker环境问题
**问题**: Docker容器无法启动
**解决方案**:
- 检查端口是否被占用
- 验证环境变量配置
- 查看容器日志: `docker logs mcp-tools-service`
- 确保数据库服务正常

## 日志查看
```bash
# 查看应用日志
tail -f logs/mcp-toolse.log

# 查看Docker日志
docker logs -f mcp-tools-service

# 查看数据库日志
docker logs -f mcp-tools-postgres
```

## 获取帮助
如果问题仍然存在:
1. 查看完整的错误堆栈
2. 检查GitHub Issues
3. 提供详细的错误信息和环境配置
"""

    @app.prompt()
    async def batch_crawler() -> str:
        """
        批量爬取最佳实践

        指导如何高效地进行大规模数据爬取
        """
        return """# 批量爬取最佳实践

## 批量爬取策略

### 1. 分时段爬取
避免在平台高峰期进行大规模爬取：
- 推荐时段: 凌晨2-6点
- 避开时段: 晚上8-10点

### 2. 分批次执行
```python
# 示例：分批爬取多个关键词
keywords_list = [
    "美妆教程",
    "护肤心得",
    "化妆技巧",
    "口红推荐"
]

for keyword in keywords_list:
    # 每个关键词爬取20条
    result = await xhs_search(
        keywords=keyword,
        max_notes=20,
        enable_comments=False  # 批量爬取时建议禁用评论
    )
    # 间隔5分钟
    await asyncio.sleep(300)
```

### 3. 增量爬取
定期爬取新增内容，避免重复：
- 记录上次爬取的最新内容ID
- 下次从该ID开始爬取
- 使用数据库去重

### 4. 错误重试机制
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
async def crawl_with_retry(keywords):
    return await xhs_search(keywords=keywords)
```

### 5. 数据验证
爬取后立即验证数据完整性：
- 检查必要字段是否存在
- 验证数据类型是否正确
- 统计爬取成功率

## 性能优化建议

### 禁用不需要的功能
```json
{
  "enable_comments": false,  // 禁用评论
  "enable_media": false,     // 禁用媒体下载
  "save_data_option": "sqlite"  // 使用数据库提高性能
}
```

### 使用数据库
对于大规模爬取，推荐使用数据库：
1. 初始化数据库: `media_crawler_init_db(db_type="sqlite")`
2. 设置save_data_option为"sqlite"或"db"
3. 数据库自动处理去重和索引

### 监控资源使用
```bash
# 监控CPU和内存
docker stats mcp-tools-service

# 监控数据库大小
docker exec mcp-tools-postgres du -sh /var/lib/postgresql/data
```

## 合规性提醒
1. 遵守平台的robots.txt规则
2. 控制爬取频率（建议每次请求间隔>=5秒）
3. 避免在短时间内大量请求
4. 仅用于学习研究，不得商业使用
5. 尊重创作者版权
"""

    get_logger().info("✅ MCP Prompt模板注册成功")