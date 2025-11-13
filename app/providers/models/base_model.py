from tortoise.models import Model
from tortoise import fields
from tortoise.manager import Manager
from tortoise.queryset import QuerySet
from datetime import datetime


# ---------- 基础模型：软删逻辑集中在这里 ----------
class BaseModel(Model):
    id = fields.IntField(primary_key=True, generated=True)
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")


    class Meta(Model.Meta):
        abstract = True

    def to_dict(self):
        # 只序列化字段，排除外键关系字段
        result = {}
        for name, field in self._meta.fields_map.items():
            # 跳过外键关系字段，避免序列化错误
            if hasattr(field, 'related_model'):
                # 对于外键字段，只获取其ID值
                if hasattr(self, f"{name}_id"):
                    result[f"{name}_id"] = getattr(self, f"{name}_id")
            else:
                value = getattr(self, name)
                # 如果字段值是 datetime 类型，转换为 ISO 格式
                if isinstance(value, datetime):
                    result[name] = value.strftime("%Y-%m-%d %H:%M:%S")  # 只保留时分秒
                else:
                    result[name] = value
        return result
