# -*- coding: utf-8 -*-
"""
Redis队列管理器 - 基于Redis的持久化发布队列
"""

import asyncio
import time
import uuid
import ujson
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable, Awaitable

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from app.config.settings import global_settings
from app.providers.logger import get_logger

logger = get_logger()

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """任务类型"""
    IMAGE = "image"
    VIDEO = "video"


@dataclass
class PublishStrategy:
    """发布策略配置"""
    min_interval: int = 30          # 最小发布间隔（秒）
    max_concurrent: int = 1         # 最大并发数
    retry_count: int = 3            # 重试次数
    retry_delay: int = 60           # 重试延迟（秒）
    daily_limit: int = 50           # 每日发布限制
    hourly_limit: int = 10          # 每小时发布限制


class PublishTask(BaseModel):
    """发布任务"""
    task_id: str = Field(..., description="任务ID")
    platform: str = Field(..., description="发布平台")
    task_type: TaskType = Field(..., description="任务类型")
    payload: Dict[str, Any] = Field(..., description="发布内容")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    priority: int = Field(default=0, description="优先级，数字越大优先级越高")
    
    created_at: float = Field(default_factory=time.time, description="创建时间")
    queued_at: Optional[float] = Field(None, description="入队时间")
    started_at: Optional[float] = Field(None, description="开始时间")
    completed_at: Optional[float] = Field(None, description="完成时间")
    
    retry_count: int = Field(default=0, description="重试次数")
    progress: int = Field(default=0, description="进度百分比")
    message: str = Field(default="", description="状态消息")
    error_detail: Optional[str] = Field(None, description="错误详情")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    
    class Config:
        use_enum_values = True


def config_to_strategy(config) -> PublishStrategy:
    """将配置转换为策略对象"""
    return PublishStrategy(
        min_interval=config.min_interval,
        max_concurrent=config.max_concurrent,
        retry_count=config.retry_count,
        retry_delay=config.retry_delay,
        daily_limit=config.daily_limit,
        hourly_limit=config.hourly_limit
    )


class RedisQueuerManager:
    """Redis队列实例管理器"""
    _instances: Dict[str, aioredis.Redis] = {}
    
    @classmethod
    def get_queue_redis(cls, platform: str) -> aioredis.Redis:
        """获取指定平台的Redis实例"""
        if platform not in cls._instances:
            pool = aioredis.ConnectionPool(
                username=global_settings.redis.user,
                host=global_settings.redis.host,
                port=global_settings.redis.port,
                password=global_settings.redis.password,
                db=global_settings.redis.db + 1,  # 使用不同的db避免冲突
                decode_responses=True,
                max_connections=100,
            )
            redis_client = aioredis.Redis(connection_pool=pool)
            cls._instances[platform] = redis_client
        return cls._instances[platform]
    
    @classmethod
    async def close_all(cls):
        """关闭所有Redis实例"""
        for redis_instance in cls._instances.values():
            await redis_instance.close()
        cls._instances.clear()


class PlatformQueuer:
    """单个平台的队列处理器"""
    
    def __init__(self, platform: str, strategy: PublishStrategy):
        self.platform = platform
        self.strategy = strategy
        self.redis = RedisQueuerManager.get_queue_redis(platform)
        
        # Redis键前缀
        self.key_prefix = f"publish_queue:{platform}"
        self.queue_key = f"{self.key_prefix}:queue"
        self.processing_key = f"{self.key_prefix}:processing"
        self.tasks_key = f"{self.key_prefix}:tasks"
        self.stats_key = f"{self.key_prefix}:stats"
        self.history_key = f"{self.key_prefix}:history"
        
        # 状态控制
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.executor: Optional[Callable] = None
    
    def set_executor(self, executor: Callable[[PublishTask], Awaitable[Dict[str, Any]]]):
        """设置任务执行器"""
        self.executor = executor
    
    async def start(self) -> None:
        """启动队列处理器"""
        if self.is_running:
            return
        
        # 恢复处理中的任务
        await self._recover_processing_tasks()
        
        self.is_running = True
        
        # 启动工作进程
        for i in range(self.strategy.max_concurrent):
            task = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"[Queuer] {self.platform} 队列已启动，工作进程数: {self.strategy.max_concurrent}")
    
    async def stop(self) -> None:
        """停止队列处理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 取消所有工作任务
        for task in self.worker_tasks:
            task.cancel()
        
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        logger.info(f"[Queuer] {self.platform} 队列已停止")
    
    async def add_task(self, task: PublishTask) -> None:
        """添加任务到队列"""
        # 检查频率限制
        if not await self._check_rate_limits():
            raise RuntimeError("发布频率超出限制")
        
        # 保存任务数据
        task.status = TaskStatus.QUEUED
        task.queued_at = time.time()
        
        task_json = ujson.dumps(task.model_dump())
        await self.redis.hset(self.tasks_key, task.task_id, task_json)
        
        # 加入优先级队列
        score = task.priority * 1000000 + (2147483647 - int(task.created_at))
        await self.redis.zadd(self.queue_key, {task.task_id: score})
        
        logger.info(f"[Queuer] {self.platform} 任务已入队: {task.task_id}")
    
    async def get_task_status(self, task_id: str) -> Optional[PublishTask]:
        """获取任务状态"""
        task_data = await self.redis.hget(self.tasks_key, task_id)
        if not task_data:
            return None
        
        task_dict = ujson.loads(task_data)
        return PublishTask.model_validate(task_dict)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        queue_size = await self.redis.zcard(self.queue_key)
        processing_count = await self.redis.scard(self.processing_key)
        
        # 发布历史统计
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        
        hourly_count = await self.redis.zcount(self.history_key, hour_ago, now)
        daily_count = await self.redis.zcount(self.history_key, day_ago, now)
        
        # 最后发布时间
        last_publish = await self.redis.get(f"{self.stats_key}:last_publish")
        last_publish_time = float(last_publish) if last_publish else 0
        
        return {
            "platform": self.platform,
            "queue_size": queue_size,
            "processing_count": processing_count,
            "daily_published": daily_count,
            "hourly_published": hourly_count,
            "last_publish_time": last_publish_time,
            "is_running": self.is_running,
            "worker_count": len(self.worker_tasks)
        }
    
    async def _worker_loop(self, worker_id: str) -> None:
        """工作循环"""
        logger.info(f"[Queuer] {self.platform} 工作进程 {worker_id} 启动")
        
        while self.is_running:
            try:
                # 检查发布间隔
                if not await self._can_publish_now():
                    await asyncio.sleep(1)
                    continue
                
                # 从队列获取任务
                task_id = await self._pop_task()
                if not task_id:
                    await asyncio.sleep(1)
                    continue
                
                # 处理任务
                await self._process_task(task_id, worker_id)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[Queuer] {self.platform} 工作进程 {worker_id} 错误: {exc}")
                await asyncio.sleep(5)
        
        logger.info(f"[Queuer] {self.platform} 工作进程 {worker_id} 停止")
    
    async def _pop_task(self) -> Optional[str]:
        """原子性弹出任务"""
        lua_script = """
        local task_id = redis.call('ZPOPMIN', KEYS[1])
        if next(task_id) then
            redis.call('SADD', KEYS[2], task_id[1])
            return task_id[1]
        end
        return nil
        """
        
        result = await self.redis.eval(lua_script, 2, self.queue_key, self.processing_key)
        return result
    
    async def _process_task(self, task_id: str, worker_id: str) -> None:
        """处理单个任务"""
        try:
            # 获取任务数据
            task_data = await self.redis.hget(self.tasks_key, task_id)
            if not task_data:
                await self.redis.srem(self.processing_key, task_id)
                return
            
            task_dict = ujson.loads(task_data)
            task = PublishTask.model_validate(task_dict)
            
            # 更新处理状态
            task.status = TaskStatus.PROCESSING
            task.started_at = time.time()
            task.message = f"工作进程 {worker_id} 开始处理"
            await self._update_task(task)
            
            logger.info(f"[Queuer] {self.platform} {worker_id} 开始处理任务: {task_id}")
            
            # 执行发布任务
            if self.executor:
                result = await self.executor(task)
            else:
                raise RuntimeError("未设置任务执行器")
            
            # 更新成功状态
            task.status = TaskStatus.SUCCESS
            task.completed_at = time.time()
            task.progress = 100
            task.result = result
            task.message = "发布成功"
            await self._update_task(task)
            
            # 记录发布历史
            await self._record_publish(time.time())
            
            logger.info(f"[Queuer] {self.platform} {worker_id} 任务处理成功: {task_id}")
            
        except Exception as exc:
            # 处理失败，检查重试
            task.retry_count += 1
            
            if task.retry_count <= self.strategy.retry_count:
                # 重新入队重试
                task.status = TaskStatus.PENDING
                task.error_detail = str(exc)
                task.message = f"第{task.retry_count}次重试"
                await self._update_task(task)
                
                # 延迟重试
                retry_time = time.time() + self.strategy.retry_delay
                await self.redis.zadd(self.queue_key, {task_id: retry_time})
                
                logger.warning(f"[Queuer] {self.platform} 任务重试: {task_id}, 重试次数: {task.retry_count}")
            else:
                # 标记失败
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error_detail = str(exc)
                task.message = f"发布失败: {str(exc)}"
                await self._update_task(task)
                
                logger.error(f"[Queuer] {self.platform} 任务失败: {task_id}, 错误: {exc}")
        
        finally:
            # 从处理中集合移除
            await self.redis.srem(self.processing_key, task_id)
    
    async def _update_task(self, task: PublishTask) -> None:
        """更新任务数据"""
        task_json = ujson.dumps(task.model_dump())
        await self.redis.hset(self.tasks_key, task.task_id, task_json)
    
    async def _record_publish(self, timestamp: float) -> None:
        """记录发布时间"""
        # 更新最后发布时间
        await self.redis.set(f"{self.stats_key}:last_publish", timestamp)
        
        # 添加到发布历史
        await self.redis.zadd(self.history_key, {str(uuid.uuid4()): timestamp})
        
        # 清理1天前的记录
        day_ago = timestamp - 86400
        await self.redis.zremrangebyscore(self.history_key, 0, day_ago)
    
    async def _can_publish_now(self) -> bool:
        """检查发布间隔"""
        last_publish = await self.redis.get(f"{self.stats_key}:last_publish")
        if not last_publish:
            return True
        
        elapsed = time.time() - float(last_publish)
        return elapsed >= self.strategy.min_interval
    
    async def _check_rate_limits(self) -> bool:
        """检查频率限制"""
        now = time.time()
        
        # 检查每小时限制
        hour_ago = now - 3600
        hourly_count = await self.redis.zcount(self.history_key, hour_ago, now)
        if hourly_count >= self.strategy.hourly_limit:
            return False
        
        # 检查每日限制
        day_ago = now - 86400
        daily_count = await self.redis.zcount(self.history_key, day_ago, now)
        if daily_count >= self.strategy.daily_limit:
            return False
        
        return True
    
    async def _recover_processing_tasks(self) -> None:
        """恢复处理中的任务"""
        processing_tasks = await self.redis.smembers(self.processing_key)
        
        if processing_tasks:
            logger.info(f"[Queuer] {self.platform} 恢复 {len(processing_tasks)} 个处理中的任务")
            
            # 重新入队
            for task_id in processing_tasks:
                score = int(time.time())
                await self.redis.zadd(self.queue_key, {task_id: score})
            
            # 清空处理中集合
            await self.redis.delete(self.processing_key)


class PublishQueue:
    """发布队列管理器 - 主入口"""
    
    def __init__(self):
        self.platform_queuers: Dict[str, PlatformQueuer] = {}
        
        # 从配置文件加载策略
        publish_config = global_settings.publish
        self.default_strategies: Dict[str, PublishStrategy] = {
            "xhs": config_to_strategy(publish_config.xhs),
        }
    
    def register_platform(
        self, 
        platform: str, 
        executor: Callable[[PublishTask], Awaitable[Dict[str, Any]]],
        strategy: Optional[PublishStrategy] = None
    ) -> None:
        """注册平台发布器"""
        if strategy is None:
            strategy = self.default_strategies.get(platform, PublishStrategy())
        
        queuer = PlatformQueuer(platform, strategy)
        queuer.set_executor(executor)
        self.platform_queuers[platform] = queuer
        
        logger.info(f"[Queuer] 注册平台: {platform}")
    
    async def start_all(self) -> None:
        """启动所有队列"""
        for queuer in self.platform_queuers.values():
            await queuer.start()
        
        logger.info("[Queuer] 所有发布队列已启动")
    
    async def stop_all(self) -> None:
        """停止所有队列"""
        for queuer in self.platform_queuers.values():
            await queuer.stop()
        
        await RedisQueuerManager.close_all()
        logger.info("[Queuer] 所有发布队列已停止")
    
    async def submit_task(self, task: PublishTask) -> None:
        """提交发布任务"""
        if task.platform not in self.platform_queuers:
            raise ValueError(f"未支持的平台: {task.platform}")
        
        queuer = self.platform_queuers[task.platform]
        await queuer.add_task(task)
    
    async def get_task_status(self, task_id: str, platform: str) -> Optional[PublishTask]:
        """获取任务状态"""
        if platform not in self.platform_queuers:
            return None
        
        return await self.platform_queuers[platform].get_task_status(task_id)
    
    async def update_platform_strategy(self, platform: str, strategy: PublishStrategy) -> None:
        """更新平台发布策略"""
        if platform not in self.platform_queuers:
            raise ValueError(f"平台 {platform} 未注册")
        
        # 停止当前队列
        queuer = self.platform_queuers[platform]
        executor = queuer.executor
        await queuer.stop()
        
        # 创建新的队列处理器
        new_queuer = PlatformQueuer(platform, strategy)
        new_queuer.set_executor(executor)
        self.platform_queuers[platform] = new_queuer
        
        # 启动新队列
        await new_queuer.start()
        
        logger.info(f"[Queuer] 更新平台 {platform} 策略: {strategy}")
    
    def get_platform_strategy(self, platform: str) -> Optional[PublishStrategy]:
        """获取平台发布策略"""
        if platform not in self.platform_queuers:
            return None
        
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有队列统计"""
        stats = {
            "total_platforms": len(self.platform_queuers),
            "platforms": {}
        }
        
        for platform, queuer in self.platform_queuers.items():
            platform_stats = await queuer.get_stats()
            # 添加策略信息
            strategy = queuer.strategy
            platform_stats["strategy"] = {
                "min_interval": strategy.min_interval,
                "max_concurrent": strategy.max_concurrent,
                "retry_count": strategy.retry_count,
                "retry_delay": strategy.retry_delay,
                "daily_limit": strategy.daily_limit,
                "hourly_limit": strategy.hourly_limit
            }
            stats["platforms"][platform] = platform_stats
        
        return stats