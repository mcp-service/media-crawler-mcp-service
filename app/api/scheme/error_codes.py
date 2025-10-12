# -*- coding: utf-8 -*-

SUCCESS = (0, 'success')
SERVER_ERROR = (-1, '服务器错误')

PAGE_NOT_FOUND = (404, '页面未找到')
NOT_METHOD_FOR_PATH = (405, '不支持的请求方法')
CUSTOM_MESSAGE_ERROR = (9, '{message}')
PERMISSION_ERROR = (403, "鉴权失败")
INVALID_TOKEN = (401, "无效的token")


# 鉴权
IAM_CALLBACK_ERROR = (20001, "获取IAM用户信息错误")
IAM_EXPIRES_ERROR = (20002, "飞书二维码已经过期，请重新扫码登录")
IAM_GET_TOKEN_ERROR = (20003, "获取access token失败")
IAM_GET_USER_INFO_ERROR = (20004, "获取用户信息失败")
USER_NOT_FOUND = (20005, "用户不存在")
TOKEN_NOT_FOUND = (20006, "token不存在")

# 知识库数据问题
NAME_DUPLICATION_ERROR = (30001, "名称重复，请确认")
ONLINE_CANNOT_UPDATE_ERROR = (30002, "有已上线的内容，请先下线后再删除")


# 通用业务错误码
PARAM_ERROR = (50001, "传入参数错误")
SYSTEM_FREQUENT_REQUESTS = (50002, "超过频率，请稍后刷新")
USER_FREQUENT_REQUESTS = (50003, "您的操作过于频繁，请稍后再试")
NOT_DATA= (50004, "没有相关的数据信息")
CHAT_ERROR = (50004, '对话服务错误')
ORM_VALIDATION_ERROR = (50005, "ORM数据验证失败")
 
