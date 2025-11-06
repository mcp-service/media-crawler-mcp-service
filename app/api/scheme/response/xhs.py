# -*- coding: utf-8 -*-
"""小红书数据模型 - AI友好的精炼数据结构"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class XhsUserInfo(BaseModel):
    """用户信息"""
    user_id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    ip_location: Optional[str] = Field(None, description="IP属地")


class XhsEngagementStats(BaseModel):
    """互动数据"""
    liked_count: str = Field(default="0", description="点赞数")
    comment_count: str = Field(default="0", description="评论数") 
    share_count: str = Field(default="0", description="分享数")
    collected_count: str = Field(default="0", description="收藏数")
    
    @property
    def total_engagement(self) -> int:
        """总互动数"""
        def safe_int(value: str) -> int:
            try:
                return int(value.replace(',', '').replace('w', '000').replace('万', '0000'))
            except (ValueError, AttributeError):
                return 0
        
        return (safe_int(self.liked_count) + safe_int(self.comment_count) + 
                safe_int(self.share_count) + safe_int(self.collected_count))
    
    @property
    def engagement_level(self) -> str:
        """互动等级"""
        total = self.total_engagement
        if total > 10000:
            return "高互动"
        elif total > 1000:
            return "中等互动"
        elif total > 100:
            return "低互动"
        else:
            return "极低互动"


class XhsMedia(BaseModel):
    """媒体内容"""
    type: str = Field(..., description="媒体类型：image/video")
    urls: List[str] = Field(default_factory=list, description="媒体文件URLs")
    count: int = Field(default=0, description="媒体文件数量")
    
    @property
    def description(self) -> str:
        """媒体描述"""
        if self.type == "video":
            return f"视频内容({self.count}个视频)"
        elif self.type == "image":
            return f"图文内容({self.count}张图片)"
        else:
            return f"其他媒体({self.count}个文件)"


class XhsNote(BaseModel):
    """小红书笔记 - AI友好的核心数据结构"""
    
    # 核心标识
    note_id: str = Field(..., description="笔记ID")
    note_url: str = Field(..., description="笔记链接")
    
    # 内容信息
    title: str = Field(..., description="笔记标题")
    content: str = Field(..., description="笔记正文内容")
    content_summary: str = Field(default="", description="内容摘要（100字以内）")
    
    # 分类信息
    note_type: str = Field(..., description="笔记类型：normal/video")
    category: str = Field(default="", description="笔记分类")
    
    # 时间信息
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    time_desc: str = Field(default="", description="发布时间描述")
    
    # 用户信息
    author: XhsUserInfo = Field(..., description="作者信息")
    
    # 互动数据
    engagement: XhsEngagementStats = Field(..., description="互动统计")
    
    # 媒体内容
    media: XhsMedia = Field(..., description="媒体内容")
    
    # 标签
    tags: List[str] = Field(default_factory=list, description="标签列表")
    topics: List[str] = Field(default_factory=list, description="话题列表")
    
    # 热度等级
    trending_level: str = Field(default="normal", description="热度等级：viral/trending/normal/low")
    
    @field_validator('content_summary')
    @classmethod
    def generate_summary(cls, v: str, info) -> str:
        """自动生成内容摘要"""
        if v:
            return v
        content = info.data.get('content', '')
        if len(content) > 100:
            return content[:100] + "..."
        return content
    
    @property
    def ai_summary(self) -> str:
        """AI可读的完整描述"""
        parts = [
            f"【{self.title}】",
            f"{self.media.description}",
            f"{self.engagement.engagement_level}",
            f"作者：{self.author.nickname}"
        ]
        if self.tags:
            parts.append(f"标签：{', '.join(self.tags[:3])}")
        if self.time_desc:
            parts.append(f"发布：{self.time_desc}")
        
        return " | ".join(parts)
    
    @classmethod
    def from_raw_data(cls, raw_data: dict) -> 'XhsNote':
        """从原始数据转换"""
        # 处理用户信息
        author = XhsUserInfo(
            user_id=str(raw_data.get('user_id', '')),
            nickname=raw_data.get('nickname', ''),
            avatar=raw_data.get('avatar'),
            ip_location=raw_data.get('ip_location')
        )
        
        # 处理互动数据
        engagement = XhsEngagementStats(
            liked_count=str(raw_data.get('liked_count', 0)),
            comment_count=str(raw_data.get('comment_count', 0)),
            share_count=str(raw_data.get('share_count', 0)),
            collected_count=str(raw_data.get('collected_count', 0))
        )
        
        # 处理媒体信息
        image_list = raw_data.get('image_list', [])
        video_url = raw_data.get('video_url', '')
        
        if video_url:
            media = XhsMedia(
                type="video",
                urls=[video_url] if isinstance(video_url, str) else video_url,
                count=1 if video_url else 0
            )
        else:
            media = XhsMedia(
                type="image", 
                urls=[img.get('url', '') for img in image_list if img.get('url')],
                count=len(image_list)
            )
        
        # 处理标签
        tag_list = raw_data.get('tag_list', [])
        tags = []
        topics = []
        for tag in tag_list:
            if isinstance(tag, dict):
                tag_name = tag.get('name', '')
                if tag_name:
                    if tag.get('type') == 'topic':
                        topics.append(tag_name)
                    else:
                        tags.append(tag_name)
        
        # 处理时间
        publish_time = None
        time_desc = ""
        if raw_data.get('time'):
            try:
                publish_time = datetime.fromtimestamp(raw_data['time'])
                now = datetime.now()
                diff = now - publish_time
                if diff.days > 0:
                    time_desc = f"{diff.days}天前"
                elif diff.seconds > 3600:
                    time_desc = f"{diff.seconds // 3600}小时前"
                else:
                    time_desc = f"{diff.seconds // 60}分钟前"
            except:
                pass
        
        # 计算热度等级
        total_engagement = engagement.total_engagement
        if total_engagement > 50000:
            trending_level = "viral"
        elif total_engagement > 10000:
            trending_level = "trending"  
        elif total_engagement > 1000:
            trending_level = "normal"
        else:
            trending_level = "low"
        
        return cls(
            note_id=raw_data.get('note_id', ''),
            note_url=raw_data.get('note_url', ''),
            title=raw_data.get('title', ''),
            content=raw_data.get('desc', ''),
            note_type=raw_data.get('type', 'normal'),
            publish_time=publish_time,
            time_desc=time_desc,
            author=author,
            engagement=engagement,
            media=media,
            tags=tags,
            topics=topics,
            trending_level=trending_level
        )


class XhsComment(BaseModel):
    """小红书评论"""
    comment_id: str = Field(..., description="评论ID")
    content: str = Field(..., description="评论内容")
    author_name: str = Field(..., description="评论者昵称")
    like_count: str = Field(default="0", description="点赞数")
    publish_time: Optional[datetime] = Field(None, description="评论时间")
    time_desc: str = Field(default="", description="时间描述")
    is_author_reply: bool = Field(default=False, description="是否为作者回复")
    
    @property
    def like_count_int(self) -> int:
        """点赞数的整数值"""
        try:
            return int(str(self.like_count).replace(',', '').replace('w', '000').replace('万', '0000'))
        except (ValueError, AttributeError):
            return 0
    
    @property
    def sentiment(self) -> str:
        """情感倾向"""
        positive_words = ['好', '棒', '喜欢', '爱了', '太美', '想要', '推荐']
        negative_words = ['不好', '差', '垃圾', '假的', '骗人', '不推荐']
        
        content = self.content.lower()
        pos_count = sum(1 for word in positive_words if word in content)
        neg_count = sum(1 for word in negative_words if word in content)
        
        if pos_count > neg_count:
            return "积极"
        elif neg_count > pos_count:
            return "消极"
        else:
            return "中性"


class XhsSearchResult(BaseModel):
    """小红书搜索结果"""
    notes: List[XhsNote] = Field(default_factory=list, description="笔记列表")
    total_count: int = Field(default=0, description="笔记总数")
    search_keyword: str = Field(default="", description="搜索关键词")
    
    # AI分析统计
    analysis: Dict[str, Any] = Field(default_factory=dict, description="数据分析")
    
    def analyze_data(self) -> Dict[str, Any]:
        """生成数据分析"""
        if not self.notes:
            return {}
        
        # 内容类型分布
        type_counts = {}
        trending_counts = {}
        total_engagement = 0
        
        for note in self.notes:
            type_counts[note.note_type] = type_counts.get(note.note_type, 0) + 1
            trending_counts[note.trending_level] = trending_counts.get(note.trending_level, 0) + 1
            total_engagement += note.engagement.total_engagement
        
        # 热门标签
        all_tags = []
        for note in self.notes:
            all_tags.extend(note.tags)
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        analysis = {
            "content_types": type_counts,
            "trending_levels": trending_counts,
            "avg_engagement": total_engagement // len(self.notes),
            "top_tags": [tag for tag, count in top_tags],
            "total_notes": len(self.notes),
            "insights": self._generate_insights()
        }
        
        self.analysis = analysis
        return analysis
    
    def _generate_insights(self) -> List[str]:
        """生成洞察"""
        if not self.notes:
            return ["无数据"]
        
        insights = []
        
        # 爆款内容比例
        viral_count = sum(1 for note in self.notes if note.trending_level == "viral")
        if viral_count > len(self.notes) * 0.3:
            insights.append("包含较多爆款内容")
        
        # 视频内容比例
        video_count = sum(1 for note in self.notes if note.note_type == "video")
        if video_count > len(self.notes) * 0.6:
            insights.append("视频内容占主导")
        else:
            insights.append("图文内容为主")
        
        # 互动活跃度
        avg_engagement = sum(note.engagement.total_engagement for note in self.notes) / len(self.notes)
        if avg_engagement > 5000:
            insights.append("整体互动活跃")
        elif avg_engagement < 500:
            insights.append("互动相对较低")
        
        return insights


class XhsCommentsResult(BaseModel):
    """小红书评论结果"""
    comments: List[XhsComment] = Field(default_factory=list, description="评论列表")
    total_count: int = Field(default=0, description="评论总数")
    note_id: str = Field(default="", description="笔记ID")
    
    # 分析数据
    sentiment_stats: Dict[str, int] = Field(default_factory=dict, description="情感分布")
    hot_comments: List[XhsComment] = Field(default_factory=list, description="热门评论")
    
    def analyze_sentiment(self):
        """分析评论情感"""
        sentiment_counts = {"积极": 0, "消极": 0, "中性": 0}
        hot_comments = []
        
        for comment in self.comments:
            sentiment_counts[comment.sentiment] += 1
            if comment.like_count_int > 10:
                hot_comments.append(comment)
        
        self.sentiment_stats = sentiment_counts
        self.hot_comments = sorted(hot_comments, key=lambda x: x.like_count_int, reverse=True)[:10]
