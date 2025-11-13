"""
市场分析接口 - Analyze Endpoint

提供市场机会和运营能力的综合分析评估
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.api.scheme.request.analyze_scheme import AnalyzeRequest
from app.api.scheme.response.analyze_response import (
    AnalyzeResponse,
    MarketOpportunityScore,
    OperationalCapabilityScore,
    RecommendationItem
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="市场分析接口",
    description="""
    # 市场分析 API

    对产品/品类进行全面的市场机会和运营能力评估，返回详细的分析报告和战略建议。

    ## 功能特点
    - **外部市场评估**: 分析市场规模、增长潜力、竞争格局、市场情绪
    - **内部能力评估**: 评估增长势能、用户质量、成本效率、产品质量、基础设施
    - **智能建议**: 基于数据自动生成战略建议和风险警示

    ## 使用场景
    1. 新品类/新品入场决策
    2. 现有业务健康度诊断
    3. 市场机会挖掘
    4. 运营优化方向指引

    ## 评分体系
    - **0-40分**: 较差 (不推荐/需要大幅改进)
    - **40-60分**: 中等 (有条件可行/需要优化)
    - **60-80分**: 良好 (推荐/小幅优化)
    - **80-100分**: 优秀 (强烈推荐/保持优势)
    """
)
async def analyze_market(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    市场分析主接口

    Args:
        request: 分析请求，包含外部市场特征、内部运营特征和可选的分析提示

    Returns:
        详细的分析报告，包括评分、等级、建议和风险警示

    Raises:
        HTTPException: 当参数验证失败或分析过程出错时
    """
    try:
        logger.info(f"开始市场分析 - 产品: {request.hints.product_name if request.hints else 'N/A'}")

        # 1. 计算市场机会评分
        market_opportunity = _calculate_market_opportunity(request)

        # 2. 计算运营能力评分
        operational_capability = _calculate_operational_capability(request)

        # 3. 计算综合评分
        comprehensive_score = (market_opportunity.overall_score * 0.5 +
                              operational_capability.overall_score * 0.5)

        # 4. 确定可行性等级
        feasibility_level = _determine_feasibility_level(
            market_opportunity.overall_score,
            operational_capability.overall_score
        )

        # 5. 生成建议
        recommendations = _generate_recommendations(request, market_opportunity, operational_capability)

        # 6. 识别风险
        risk_warnings = _identify_risks(request)

        # 7. 生成关键洞察
        key_insights = _generate_key_insights(request)

        response = AnalyzeResponse(
            product_name=request.hints.product_name if request.hints else None,
            analysis_timestamp=datetime.utcnow().isoformat() + "Z",
            market_opportunity=market_opportunity,
            operational_capability=operational_capability,
            comprehensive_score=round(comprehensive_score, 2),
            feasibility_level=feasibility_level,
            recommendations=recommendations,
            risk_warnings=risk_warnings,
            key_insights=key_insights
        )

        logger.info(f"市场分析完成 - 综合评分: {comprehensive_score:.2f}, 等级: {feasibility_level}")
        return response

    except Exception as e:
        logger.error(f"市场分析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析过程出错: {str(e)}"
        )


def _calculate_market_opportunity(request: AnalyzeRequest) -> MarketOpportunityScore:
    """计算市场机会评分"""
    ext = request.features.external

    # 1. 市场规模得分 (基于TAM和增长率)
    size_score = min(100, (ext.industry_size_tam / 10) * 10)  # 假设10亿为满分基准
    growth_bonus = max(0, min(20, ext.industry_cagr_3y * 40))  # CAGR加成
    market_size_score = min(100, size_score + growth_bonus)

    # 2. 增长潜力得分 (趋势+CAGR)
    trend_score = (ext.trend_index_90d_slope + 1) * 50  # 转换到0-100
    cagr_score = max(0, min(100, (ext.industry_cagr_3y + 0.2) * 100))
    growth_potential_score = (trend_score * 0.4 + cagr_score * 0.6)

    # 3. 竞争强度得分 (分数越高表示竞争越小,越有机会)
    # HHI越高 -> 竞争越小 -> 机会可能更小(寡头垄断) 或 更大(打破垄断)
    # 这里采用中等集中度最优的逻辑
    if ext.head_concentration_hhi < 0.15:
        competition_base = 60  # 充分竞争,中等机会
    elif ext.head_concentration_hhi < 0.25:
        competition_base = 70  # 中等集中,较好机会
    else:
        competition_base = 50  # 高集中度,机会较小

    # 头部份额越大,机会越小
    share_penalty = ext.category_rank_top_share * 30
    competition_intensity_score = max(0, competition_base - share_penalty)

    # 4. 市场情绪得分
    # 声量和情感综合
    mentions_score = min(100, (ext.mentions_30d / 100))  # 假设10000为满分
    sentiment_score = (ext.sentiment_mean + 1) * 50  # 转换到0-100
    market_sentiment_score = (mentions_score * 0.3 + sentiment_score * 0.7)

    # 综合得分
    overall = (
        market_size_score * 0.3 +
        growth_potential_score * 0.3 +
        competition_intensity_score * 0.2 +
        market_sentiment_score * 0.2
    )

    # 确定等级
    if overall >= 80:
        level = "excellent"
        summary = "市场机会优秀，强烈建议进入"
    elif overall >= 60:
        level = "good"
        summary = "市场机会良好，建议进入"
    elif overall >= 40:
        level = "medium"
        summary = "市场机会中等，需谨慎评估"
    else:
        level = "poor"
        summary = "市场机会较差，不建议进入"

    return MarketOpportunityScore(
        overall_score=round(overall, 2),
        market_size_score=round(market_size_score, 2),
        growth_potential_score=round(growth_potential_score, 2),
        competition_intensity_score=round(competition_intensity_score, 2),
        market_sentiment_score=round(market_sentiment_score, 2),
        level=level,
        summary=summary
    )


def _calculate_operational_capability(request: AnalyzeRequest) -> OperationalCapabilityScore:
    """计算运营能力评分"""
    internal = request.features.internal

    # 1. 增长势能得分
    gmv_score = max(0, min(100, (internal.gmv_mom_3m + 0.2) * 100))
    growth_momentum_score = gmv_score

    # 2. 用户质量得分 (留存率)
    user_quality_score = internal.retention_d7 * 100

    # 3. 成本效率得分 (CAC越低越好)
    # 假设CAC=50为优秀,200为及格,500为较差
    if internal.cac_or_cpa <= 50:
        cost_efficiency_score = 100
    elif internal.cac_or_cpa <= 200:
        cost_efficiency_score = 100 - (internal.cac_or_cpa - 50) * 0.4
    else:
        cost_efficiency_score = max(0, 40 - (internal.cac_or_cpa - 200) * 0.1)

    # 4. 产品质量得分 (退货率和差评率)
    refund_penalty = internal.refund_rate * 100
    bad_review_penalty = internal.bad_review_ratio * 100
    product_quality_score = 100 - (refund_penalty + bad_review_penalty) / 2

    # 5. 基础设施得分 (渠道覆盖+供应链)
    infrastructure_score = (internal.channel_coverage * 0.4 + internal.supply_readiness * 0.6) * 100

    # 综合得分
    overall = (
        growth_momentum_score * 0.25 +
        user_quality_score * 0.25 +
        cost_efficiency_score * 0.2 +
        product_quality_score * 0.15 +
        infrastructure_score * 0.15
    )

    # 确定等级
    if overall >= 80:
        level = "strong"
        summary = "运营能力强，具备良好执行基础"
    elif overall >= 60:
        level = "good"
        summary = "运营能力良好，有优化空间"
    elif overall >= 40:
        level = "medium"
        summary = "运营能力中等，需要改进"
    else:
        level = "weak"
        summary = "运营能力较弱，需要大幅提升"

    return OperationalCapabilityScore(
        overall_score=round(overall, 2),
        growth_momentum_score=round(growth_momentum_score, 2),
        user_quality_score=round(user_quality_score, 2),
        cost_efficiency_score=round(cost_efficiency_score, 2),
        product_quality_score=round(product_quality_score, 2),
        infrastructure_score=round(infrastructure_score, 2),
        level=level,
        summary=summary
    )


def _determine_feasibility_level(market_score: float, operational_score: float) -> str:
    """确定可行性等级"""
    avg_score = (market_score + operational_score) / 2

    if avg_score >= 75 and min(market_score, operational_score) >= 60:
        return "highly_recommended"
    elif avg_score >= 60:
        return "recommended"
    elif avg_score >= 45:
        return "conditional"
    else:
        return "not_recommended"


def _generate_recommendations(
    request: AnalyzeRequest,
    market: MarketOpportunityScore,
    operational: OperationalCapabilityScore
) -> list[RecommendationItem]:
    """生成战略建议"""
    recommendations = []
    internal = request.features.internal

    # 基于留存率的建议
    if internal.retention_d7 < 0.4:
        recommendations.append(RecommendationItem(
            priority="high",
            category="运营优化",
            title="提升用户留存率",
            description=f"当前7日留存率{internal.retention_d7*100:.1f}%偏低，建议优化用户体验、增值服务和用户触达策略",
            expected_impact="预计可提升留存率至45%+，带来GMV增长15-20%"
        ))

    # 基于CAC的建议
    if internal.cac_or_cpa > 200:
        recommendations.append(RecommendationItem(
            priority="high",
            category="成本优化",
            title="降低获客成本",
            description=f"当前获客成本{internal.cac_or_cpa:.0f}元偏高，建议优化投放策略、提升转化率、探索低成本渠道",
            expected_impact="预计可降低CAC至150元以下，提升营销ROI 30%+"
        ))

    # 基于差评率的建议
    if internal.bad_review_ratio > 0.15:
        recommendations.append(RecommendationItem(
            priority="medium",
            category="产品改进",
            title="改善产品质量和用户满意度",
            description=f"差评率{internal.bad_review_ratio*100:.1f}%较高，建议分析差评原因，针对性改进产品和服务",
            expected_impact="预计可降低差评率至10%以下，提升复购率"
        ))

    # 基于竞争格局的建议
    if market.competition_intensity_score < 60:
        recommendations.append(RecommendationItem(
            priority="high",
            category="市场策略",
            title="明确差异化定位",
            description="市场竞争激烈，建议从产品特性、目标人群、价格带等维度找到差异化切入点",
            expected_impact="建立竞争壁垒，提升品牌认知度"
        ))

    # 基于渠道覆盖的建议
    if internal.channel_coverage < 0.6:
        recommendations.append(RecommendationItem(
            priority="medium",
            category="渠道拓展",
            title="扩大渠道覆盖",
            description=f"当前渠道覆盖率{internal.channel_coverage*100:.0f}%，建议拓展新渠道以提升市场渗透",
            expected_impact="预计可提升GMV 20-30%"
        ))

    return recommendations[:5]  # 最多返回5条建议


def _identify_risks(request: AnalyzeRequest) -> list[str]:
    """识别主要风险"""
    risks = []
    ext = request.features.external
    internal = request.features.internal

    # 市场风险
    if ext.head_concentration_hhi > 0.3:
        risks.append("市场高度集中，头部品牌壁垒较高，新进入者面临较大挑战")

    if ext.trend_index_90d_slope < 0:
        risks.append("市场趋势下滑，需关注是否为季节性波动还是长期趋势")

    if ext.sentiment_mean < 0.3:
        risks.append("市场情绪偏负面，需要审慎评估品类/产品的用户接受度")

    # 运营风险
    if internal.gmv_mom_3m < 0:
        risks.append("GMV负增长，业务健康度堪忧，需要紧急止血")

    if internal.refund_rate > 0.15:
        risks.append("退货率较高，可能存在产品质量或物流问题")

    if internal.supply_readiness < 0.5:
        risks.append("供应链准备不足，可能影响业务扩张和用户体验")

    return risks


def _generate_key_insights(request: AnalyzeRequest) -> dict:
    """生成关键洞察"""
    ext = request.features.external
    internal = request.features.internal

    insights = {}

    # 市场趋势洞察
    if ext.trend_index_90d_slope > 0.1:
        insights["market_trend"] = "市场处于快速增长期，90天趋势呈明显上升态势，机会窗口期较好"
    elif ext.trend_index_90d_slope < -0.1:
        insights["market_trend"] = "市场趋势下滑，需要关注是否为季节性因素或行业周期性调整"
    else:
        insights["market_trend"] = "市场趋势平稳，属于成熟期市场"

    # 竞争格局洞察
    if ext.head_concentration_hhi < 0.15:
        insights["competitive_landscape"] = "充分竞争市场，品牌集中度低，有较多机会但需要明确差异化"
    elif ext.head_concentration_hhi < 0.25:
        insights["competitive_landscape"] = "中等集中度市场，头部品牌有一定优势但仍有突围空间"
    else:
        insights["competitive_landscape"] = "寡头垄断市场，需要找到细分切入点或创新模式"

    # 声量分析
    if ext.mentions_7d > 0 and ext.mentions_30d > 0:
        daily_avg_7d = ext.mentions_7d / 7
        daily_avg_30d = ext.mentions_30d / 30
        if daily_avg_7d > daily_avg_30d * 1.5:
            insights["voice_trend"] = "近期声量显著上升，可能有热点事件或营销活动驱动"
        elif daily_avg_7d < daily_avg_30d * 0.7:
            insights["voice_trend"] = "近期声量下降，需要关注市场热度变化"

    # 运营健康度
    if internal.retention_d7 > 0.4 and internal.gmv_mom_3m > 0.15:
        insights["operational_health"] = "用户留存和GMV增长均表现良好，业务进入良性循环"
    elif internal.retention_d7 < 0.3 or internal.gmv_mom_3m < 0:
        insights["operational_health"] = "用户留存或增长存在问题，需要重点关注并优化"

    return insights