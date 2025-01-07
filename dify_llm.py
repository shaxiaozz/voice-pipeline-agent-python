import json
import time
import uuid
import aiohttp
from typing import AsyncIterator, Optional, Any
from livekit.agents import llm, metrics
from livekit.rtc import EventEmitter

class DifyLLM(llm.LLM, EventEmitter):
    def __init__(self, api_key: str, api_url: str, username: str = None):
        super().__init__()  # 初始化 EventEmitter
        self.api_key = api_key
        self.api_url = api_url
        self._events = {}  # 初始化事件字典
        self.username = username or str(uuid.uuid4())
        
    async def chat(
        self,
        chat_ctx: llm.ChatContext,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fnc_ctx: Any = None,
    ) -> AsyncIterator[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        payload = {
            "inputs": {
                "username": self.username
            },
            "query": chat_ctx.messages[-1].content if chat_ctx.messages else "",
            "response_mode": "streaming",
            "conversation_id": "",
            "user": "livekit-agent"
        }

        tokens_used = 0
        start_time = time.time()
        error = None
        prompt_tokens = len(payload["query"].split())
        completion_tokens = 0
        request_id = str(uuid.uuid4())
        first_token_time = None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error = f"Dify API request failed with status {response.status}"
                        raise Exception(error)
                    
                    # 处理 SSE 流式响应
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]  # 移除 'data: ' 前缀
                            if data == '[DONE]':
                                break
                            try:
                                json_data = json.loads(data)
                                if 'answer' in json_data:
                                    if first_token_time is None:
                                        first_token_time = time.time()
                                    answer_tokens = len(json_data['answer'].split())
                                    completion_tokens += answer_tokens
                                    tokens_used += answer_tokens
                                    yield json_data['answer']
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            error = str(e)
            raise
        finally:
            duration = time.time() - start_time
            total_tokens = prompt_tokens + completion_tokens
            tokens_per_second = total_tokens / duration if duration > 0 else 0
            ttft = (first_token_time - start_time) if first_token_time else 0

            # 创建完整的指标对象
            llm_metrics = metrics.LLMMetrics(
                duration=duration,
                label="dify",
                cancelled=False,
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                tokens_per_second=tokens_per_second,
                error=error,
                request_id=request_id,           # 新增：请求ID
                timestamp=int(start_time),       # 新增：开始时间戳
                ttft=ttft                        # 新增：首个令牌时间 (Time To First Token)
            )
            # 发送指标收集事件
            self.emit("metrics_collected", llm_metrics) 
