# -*- coding: utf-8 -*-
import time
import json
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Dict, Any, Optional
from starlette.responses import JSONResponse, StreamingResponse
from app.providers.logger import get_logger
from app.api.scheme import error_codes


# 统一 JSON 返回
def jsonify_response(data: Optional[Dict[str, Any]] = None, status_response: Optional[tuple] = None, extends: Optional[Dict[str, Any]] = None) -> JSONResponse:
    if data is None:
        data = {}
    
    # 处理状态响应
    if status_response is None:
        status_dict = {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1]
        }
    else:
        status_dict = {
            "code": status_response[0],
            "msg": status_response[1]
        }
    ret = {"data": data}
    ret.update(**status_dict)
    if extends:
        ret.update(**extends)
    return JSONResponse(content=ret)

# 流式响应封装
async def stream_json_response(data_generator=None, error_response=None, media_type="text/event-stream"):
    async def stream_generator():
        if data_generator:
            async for chunk in data_generator:
                yield chunk
        else:
            # 如果提供了error_response，创建一个状态数据生成器
            try:
                if error_response is None:
                    response = {"code": error_codes.SUCCESS[0], "msg": error_codes.SUCCESS[1]}
                else:
                    response = {"code": error_response[0], "msg": error_response[1]}

                data = f"data: {{\"code\": {response['code']}, \"msg\": \"{response['msg']}\"}}\n\n"
                await asyncio.sleep(0)  # 异步操作
                yield data
            except Exception as e:
                get_logger().error(f"Stream generation error: {e}")
                yield "data: {\"code\": 500, \"msg\": \"Internal Server Error\"}\n\n"

    return StreamingResponse(stream_generator(), media_type=media_type)


async def consume_and_yield(queue: asyncio.Queue) -> AsyncGenerator:
    while True:
        try:
            item = await queue.get()
            if item is None:
                break
            yield item
        except Exception as e:
            get_logger().error(f"Error consuming item from queue: {e}")
            break
        