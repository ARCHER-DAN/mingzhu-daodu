"""
Dify 对话代理路由
POST /api/chat-messages → Dify SSE 流式转发

保持与现有 serve_frontend.py 的行为一致：
- 请求体原样转发到 Dify /v1/chat-messages
- 透传请求头（排除 host、content-length、authorization）
- 替换 Authorization 头为 DIFY_APP_API_KEY
- SSE 流式响应逐块转发给客户端
"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from server.config import DIFY_BASE_URL, DIFY_APP_API_KEY
from server.middleware.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["chat"])

DIFY_CHAT_URL = f"{DIFY_BASE_URL}/v1/chat-messages"


async def _proxy_dify_stream(request: Request, body: bytes):
    """代理 Dify SSE 流式请求，逐块转发响应"""
    headers = {}
    for k, v in request.headers.items():
        if k.lower() in ('host', 'content-length', 'authorization'):
            continue
        headers[k] = v
    if DIFY_APP_API_KEY:
        headers['Authorization'] = f'Bearer {DIFY_APP_API_KEY}'

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            'POST',
            DIFY_CHAT_URL,
            headers=headers,
            content=body,
        ) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk


@router.post(
    "/chat-messages",
    summary="Dify 对话代理（SSE 流式）",
    responses={
        200: {"description": "SSE 流式响应，逐块返回 AI 生成的回答"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("20/minute")
async def proxy_chat(request: Request):
    """Dify 对话代理 —— 请求体原样转发到 Dify /v1/chat-messages，SSE 流式返回。

    请求格式与 Dify advanced-chat API 一致，需包含 query、conversation_id 等字段。
    响应为 text/event-stream，每个 SSE 事件包含 AI 回答的一个 token 片段，
    最终以 message_end 事件结束。
    """
    body = await request.body()
    return StreamingResponse(
        _proxy_dify_stream(request, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
