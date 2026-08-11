import logging
import time
from typing import Dict, List

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("agent.model")


class AgentModelClient:
    def __init__(self):
        self.api_key = settings.AGENT_API_KEY
        self.model = settings.AGENT_MODEL
        self.base_url = settings.AGENT_BASE_URL.rstrip("/")

    async def complete(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            logger.error("model_request_rejected reason=api_key_missing model=%s", self.model)
            raise RuntimeError("AGENT_API_KEY未配置")
        started_at = time.perf_counter()
        logger.info(
            "model_request_started model=%s message_count=%d timeout_seconds=%d "
            "force_ipv4=%s thinking=false",
            self.model,
            len(messages),
            settings.AGENT_TIMEOUT_SECONDS,
            settings.AGENT_FORCE_IPV4,
        )
        local_address = "0.0.0.0" if settings.AGENT_FORCE_IPV4 else None
        transport = httpx.AsyncHTTPTransport(
            local_address=local_address,
            retries=1,
        )
        timeout = httpx.Timeout(
            settings.AGENT_TIMEOUT_SECONDS,
            connect=min(settings.AGENT_TIMEOUT_SECONDS, 15),
        )
        try:
            async with httpx.AsyncClient(transport=transport, timeout=timeout) as http_client:
                client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=http_client,
                    max_retries=0,
                )
                response = await client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    max_tokens=settings.AGENT_MAX_OUTPUT_TOKENS,
                    response_format={"type": "json_object"},
                    extra_body={"enable_thinking": False},
                    messages=[{"role": "system", "content": system_prompt}, *messages],
                )
        except APIStatusError as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.error(
                "model_request_failed model=%s status=%s elapsed_ms=%.2f",
                self.model,
                exc.status_code,
                elapsed_ms,
            )
            raise RuntimeError(f"Agent模型请求失败: HTTP {exc.status_code}") from exc
        except APITimeoutError as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.error(
                "model_request_failed model=%s error_type=timeout elapsed_ms=%.2f",
                self.model,
                elapsed_ms,
            )
            raise RuntimeError("Agent模型请求超时") from exc
        except APIConnectionError as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.error(
                "model_request_failed model=%s error_type=connection elapsed_ms=%.2f",
                self.model,
                elapsed_ms,
            )
            raise RuntimeError("Agent模型连接失败") from exc

        if not response.choices or response.choices[0].message.content is None:
            logger.error("model_response_invalid model=%s", self.model)
            raise RuntimeError("Agent模型返回格式无效")
        content = response.choices[0].message.content
        if len(content.encode("utf-8")) > 1024 * 1024:
            raise RuntimeError("Agent模型响应超过1MiB限制")
        usage = response.usage
        logger.info(
            "model_request_completed model=%s request_id=%s elapsed_ms=%.2f "
            "prompt_tokens=%s completion_tokens=%s",
            self.model,
            response.id,
            (time.perf_counter() - started_at) * 1000,
            usage.prompt_tokens if usage else "-",
            usage.completion_tokens if usage else "-",
        )
        return content
