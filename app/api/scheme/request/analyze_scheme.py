"""
市场分析接口的请求模型定义
用于评估产品/品类的市场机会和内部运营能力
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExternalFeaturesRequest(BaseModel):
    """
    外部市场特征 - 评估市场机会和外部环境
    """

    industry_size_tam: float = Field(
        ...,
        ge=0,
        description="行业规模TAM (Total Addressable Market)，单位：亿元。"
                    "表示目标市场的总体规模，用于评估市场容量"
    )

    industry_cagr_3y: float = Field(
        ...,
        ge=-1,
        le=10,
        description="行业3年复合增长率CAGR (Compound Annual Growth Rate)。"
                    "范围：-1.0 ~ 10.0 (即 -100% ~ 1000%)。"
                    "正值表示增长，负值表示萎缩"
    )

    trend_index_90d_slope: float = Field(
        ...,
        ge=-1,
        le=1,
        description="90天趋势指数斜率。"
                    "范围：-1.0 ~ 1.0。"
                    "通过搜索热度、社交媒体讨论度等计算，衡量短期趋势变化"
    )

    category_rank_top_share: float = Field(
        ...,
        ge=0,
        le=1,
        description="品类头部集中度 - Top品牌市场份额总和。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "值越高表示头部品牌占据的市场份额越大，竞争壁垒越高"
    )

    head_concentration_hhi: float = Field(
        ...,
        ge=0,
        le=1,
        description="HHI指数 (Herfindahl-Hirschman Index) - 市场集中度指标。"
                    "范围：0.0 ~ 1.0。"
                    "0.15以下=低集中度(充分竞争)，0.15~0.25=中等集中度，0.25以上=高集中度(寡头垄断)"
    )

    mentions_7d: int = Field(
        ...,
        ge=0,
        description="近7天声量(提及次数)。"
                    "统计社交媒体、电商评论、论坛等渠道的产品/品类提及次数，"
                    "反映短期市场热度"
    )

    mentions_30d: int = Field(
        ...,
        ge=0,
        description="近30天声量(提及次数)。"
                    "统计社交媒体、电商评论、论坛等渠道的产品/品类提及次数，"
                    "反映中期市场热度和稳定性"
    )

    sentiment_mean: float = Field(
        ...,
        ge=-1,
        le=1,
        description="平均情感得分。"
                    "范围：-1.0 ~ 1.0。"
                    "-1.0=完全负面，0.0=中性，1.0=完全正面。"
                    "通过NLP分析用户评论和讨论得出"
    )

    @field_validator('mentions_30d')
    @classmethod
    def validate_mentions_consistency(cls, v, info):
        """验证30天声量应该大于等于7天声量"""
        if 'mentions_7d' in info.data and v < info.data['mentions_7d']:
            raise ValueError('mentions_30d 应该大于等于 mentions_7d')
        return v


class InternalFeaturesRequest(BaseModel):
    """
    内部运营特征 - 评估自身运营能力和执行效率
    """

    gmv_mom_3m: float = Field(
        ...,
        ge=-1,
        le=10,
        description="GMV环比增长率 (3个月)。"
                    "范围：-1.0 ~ 10.0 (即 -100% ~ 1000%)。"
                    "衡量销售额增长趋势，正值表示增长"
    )

    retention_d7: float = Field(
        ...,
        ge=0,
        le=1,
        description="7日留存率。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "用户在首次访问/购买后7天内再次访问/复购的比例"
    )

    cac_or_cpa: float = Field(
        ...,
        ge=0,
        description="CAC (Customer Acquisition Cost) 或 CPA (Cost Per Action)。"
                    "单位：元。"
                    "获取单个客户或转化的成本，值越低表示营销效率越高"
    )

    refund_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="退货率/退款率。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "值越低表示产品质量和用户满意度越高"
    )

    bad_review_ratio: float = Field(
        ...,
        ge=0,
        le=1,
        description="差评率 (1-2星评价占比)。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "值越低表示用户满意度越高"
    )

    channel_coverage: float = Field(
        ...,
        ge=0,
        le=1,
        description="渠道覆盖率。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "已覆盖的渠道数量/目标渠道总数，衡量市场渗透能力"
    )

    supply_readiness: float = Field(
        ...,
        ge=0,
        le=1,
        description="供应链就绪度。"
                    "范围：0.0 ~ 1.0 (即 0% ~ 100%)。"
                    "综合评估库存、生产能力、物流等供应链各环节的准备程度"
    )


class AnalyzeHintsRequest(BaseModel):
    """
    分析提示信息 - 提供额外的上下文信息辅助分析
    """

    industry_keywords: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="行业关键词列表。"
                    "例如：['新能源', '充电桩', '智能硬件']。"
                    "用于更精准地定位行业和竞争环境"
    )

    product_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="产品名称。"
                    "例如：'便携式充电桩'。"
                    "用于生成更具针对性的分析报告"
    )

    target_market: Optional[str] = Field(
        default=None,
        max_length=100,
        description="目标市场/人群。"
                    "例如：'一线城市新能源车主'、'95后年轻女性'。"
                    "用于细分市场分析"
    )

    competitor_names: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="主要竞争对手名称列表。"
                    "例如：['特斯拉', '小鹏', '蔚来']。"
                    "用于竞争格局分析"
    )

    @field_validator('industry_keywords', 'competitor_names')
    @classmethod
    def validate_list_items(cls, v):
        """验证列表中的每个元素不能为空"""
        if v:
            if any(not item.strip() for item in v):
                raise ValueError('列表中不能包含空字符串')
        return v


class AnalyzeRequest(BaseModel):
    """
    市场分析请求主模型

    整合外部市场特征、内部运营特征和分析提示，
    用于全面评估产品/品类的市场机会和可行性

    使用示例:
    ```json
    {
      "features": {
        "external": {
          "industry_size_tam": 500,
          "industry_cagr_3y": 0.25,
          "trend_index_90d_slope": 0.15,
          "category_rank_top_share": 0.45,
          "head_concentration_hhi": 0.35,
          "mentions_7d": 1200,
          "mentions_30d": 3500,
          "sentiment_mean": 0.65
        },
        "internal": {
          "gmv_mom_3m": 0.20,
          "retention_d7": 0.35,
          "cac_or_cpa": 150,
          "refund_rate": 0.08,
          "bad_review_ratio": 0.12,
          "channel_coverage": 0.6,
          "supply_readiness": 0.75
        }
      },
      "hints": {
        "industry_keywords": ["新能源", "充电桩"],
        "product_name": "便携式充电桩",
        "target_market": "一线城市新能源车主"
      }
    }
    ```
    """

    features: "FeaturesRequest" = Field(
        ...,
        description="特征数据，包含外部市场特征和内部运营特征"
    )

    hints: Optional[AnalyzeHintsRequest] = Field(
        default=None,
        description="可选的分析提示信息，用于提供额外的上下文"
    )


class FeaturesRequest(BaseModel):
    """
    特征数据容器 - 组合外部和内部特征
    """

    external: ExternalFeaturesRequest = Field(
        ...,
        description="外部市场特征"
    )

    internal: InternalFeaturesRequest = Field(
        ...,
        description="内部运营特征"
    )


# 更新 AnalyzeRequest 的类型引用
AnalyzeRequest.model_rebuild()
