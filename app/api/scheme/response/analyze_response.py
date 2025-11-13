"""
市场分析接口的响应模型定义
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MarketOpportunityScore(BaseModel):
    """市场机会评分"""

    overall_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="综合评分 (0-100分)。"
                    "整合所有外部市场指标计算得出，分数越高表示市场机会越好"
    )

    market_size_score: float = Field(..., ge=0, le=100, description="市场规模得分")
    growth_potential_score: float = Field(..., ge=0, le=100, description="增长潜力得分")
    competition_intensity_score: float = Field(..., ge=0, le=100, description="竞争强度得分 (分数越高表示竞争越小)")
    market_sentiment_score: float = Field(..., ge=0, le=100, description="市场情绪得分")

    level: str = Field(
        ...,
        description="机会等级: 'excellent' (优秀, 80+), 'good' (良好, 60-80), "
                    "'medium' (中等, 40-60), 'poor' (较差, <40)"
    )

    summary: str = Field(..., description="评分总结说明")


class OperationalCapabilityScore(BaseModel):
    """运营能力评分"""

    overall_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="综合评分 (0-100分)。"
                    "整合所有内部运营指标计算得出，分数越高表示运营能力越强"
    )

    growth_momentum_score: float = Field(..., ge=0, le=100, description="增长势能得分")
    user_quality_score: float = Field(..., ge=0, le=100, description="用户质量得分")
    cost_efficiency_score: float = Field(..., ge=0, le=100, description="成本效率得分")
    product_quality_score: float = Field(..., ge=0, le=100, description="产品质量得分")
    infrastructure_score: float = Field(..., ge=0, le=100, description="基础设施得分")

    level: str = Field(
        ...,
        description="能力等级: 'strong' (强, 80+), 'good' (良好, 60-80), "
                    "'medium' (中等, 40-60), 'weak' (弱, <40)"
    )

    summary: str = Field(..., description="评分总结说明")


class RecommendationItem(BaseModel):
    """单条建议"""

    priority: str = Field(..., description="优先级: 'high', 'medium', 'low'")
    category: str = Field(..., description="建议类别: '市场策略', '运营优化', '产品改进' 等")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="详细说明")
    expected_impact: str = Field(..., description="预期影响")


class AnalyzeResponse(BaseModel):
    """
    市场分析响应模型

    返回详细的市场机会评估、运营能力评估和战略建议
    """

    # 基本信息
    product_name: Optional[str] = Field(None, description="产品名称")
    analysis_timestamp: str = Field(..., description="分析时间戳 (ISO 8601格式)")

    # 核心评分
    market_opportunity: MarketOpportunityScore = Field(..., description="市场机会评分")
    operational_capability: OperationalCapabilityScore = Field(..., description="运营能力评分")

    # 综合评估
    comprehensive_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="综合评分 (0-100分)。"
                    "市场机会和运营能力的加权平均，反映整体可行性"
    )

    feasibility_level: str = Field(
        ...,
        description="可行性等级: 'highly_recommended' (强烈推荐), 'recommended' (推荐), "
                    "'conditional' (有条件可行), 'not_recommended' (不推荐)"
    )

    # 战略建议
    recommendations: list[RecommendationItem] = Field(
        ...,
        description="战略建议列表，按优先级排序"
    )

    # 风险提示
    risk_warnings: list[str] = Field(
        default_factory=list,
        description="主要风险警示"
    )

    # 关键指标洞察
    key_insights: Dict[str, Any] = Field(
        default_factory=dict,
        description="关键指标的深度洞察，包括异常值、趋势分析等"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_name": "便携式充电桩",
                "analysis_timestamp": "2025-11-09T10:30:00Z",
                "market_opportunity": {
                    "overall_score": 78.5,
                    "market_size_score": 85,
                    "growth_potential_score": 82,
                    "competition_intensity_score": 65,
                    "market_sentiment_score": 82,
                    "level": "good",
                    "summary": "市场规模充足，增长潜力大，但竞争较为激烈"
                },
                "operational_capability": {
                    "overall_score": 68.2,
                    "growth_momentum_score": 75,
                    "user_quality_score": 60,
                    "cost_efficiency_score": 55,
                    "product_quality_score": 73,
                    "infrastructure_score": 78,
                    "level": "good",
                    "summary": "运营基础较好，但在用户留存和成本控制方面有提升空间"
                },
                "comprehensive_score": 73.4,
                "feasibility_level": "recommended",
                "recommendations": [
                    {
                        "priority": "high",
                        "category": "运营优化",
                        "title": "提升用户留存率",
                        "description": "当前7日留存率35%低于行业平均水平，建议优化用户体验和增值服务",
                        "expected_impact": "预计可提升留存率至45%+，带来GMV增长15%"
                    }
                ],
                "risk_warnings": [
                    "市场竞争激烈，需要明确差异化定位",
                    "获客成本较高，需要优化营销ROI"
                ],
                "key_insights": {
                    "market_trend": "行业处于快速增长期，90天趋势呈上升态势",
                    "competitive_landscape": "中等集中度市场，仍有机会突围"
                }
            }
        }
