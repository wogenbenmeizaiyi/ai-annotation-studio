import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("agent.model")


class AgentModelClient:
    READ_TIMEOUT_RETRIES = 1
    RETRY_BACKOFF_SECONDS = 2

    def __init__(self):
        self.api_key = settings.AGENT_API_KEY
        self.model = settings.AGENT_MODEL
        self.base_url = settings.AGENT_BASE_URL.rstrip("/")

    async def complete(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            logger.error("model_request_rejected reason=api_key_missing model=%s", self.model)
            raise RuntimeError("AGENT_API_KEY未配置")
        started_at = time.perf_counter()
        local_address = "0.0.0.0" if settings.AGENT_FORCE_IPV4 else None
        timeout = httpx.Timeout(
            connect=min(settings.AGENT_TIMEOUT_SECONDS, 15),
            read=settings.AGENT_TIMEOUT_SECONDS,
            write=min(settings.AGENT_TIMEOUT_SECONDS, 30),
            pool=min(settings.AGENT_TIMEOUT_SECONDS, 15),
        )
        response = None
        max_attempts = self.READ_TIMEOUT_RETRIES + 1
        for attempt in range(1, max_attempts + 1):
            logger.info(
                "model_request_started model=%s message_count=%d read_timeout_seconds=%d "
                "connect_timeout_seconds=%d force_ipv4=%s thinking=false attempt=%d/%d",
                self.model,
                len(messages),
                settings.AGENT_TIMEOUT_SECONDS,
                min(settings.AGENT_TIMEOUT_SECONDS, 15),
                settings.AGENT_FORCE_IPV4,
                attempt,
                max_attempts,
            )
            transport = httpx.AsyncHTTPTransport(
                local_address=local_address,
                retries=1,
            )
            try:
                async with httpx.AsyncClient(
                    transport=transport,
                    timeout=timeout,
                ) as http_client:
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
                break
            except APIStatusError as exc:
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                error_code = self._status_error_code(exc)
                logger.error(
                    "model_request_failed model=%s status=%s error_code=%s "
                    "request_id=%s elapsed_ms=%.2f attempt=%d/%d",
                    self.model,
                    exc.status_code,
                    error_code or "-",
                    getattr(exc, "request_id", None) or "-",
                    elapsed_ms,
                    attempt,
                    max_attempts,
                )
                if exc.status_code == 429:
                    raise RuntimeError(
                        "Agent服务额度不足或请求受限，请检查百炼余额、额度和限流设置"
                    ) from exc
                raise RuntimeError(f"Agent模型请求失败: HTTP {exc.status_code}") from exc
            except APITimeoutError as exc:
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                timeout_type = self._timeout_type(exc)
                should_retry = timeout_type == "read" and attempt < max_attempts
                log = logger.warning if should_retry else logger.error
                log(
                    "model_request_failed model=%s error_type=%s_timeout elapsed_ms=%.2f "
                    "attempt=%d/%d retrying=%s",
                    self.model,
                    timeout_type,
                    elapsed_ms,
                    attempt,
                    max_attempts,
                    should_retry,
                )
                if should_retry:
                    await asyncio.sleep(self.RETRY_BACKOFF_SECONDS * attempt)
                    continue
                if timeout_type == "connect":
                    raise RuntimeError("Agent模型连接超时") from exc
                raise RuntimeError("Agent模型响应超时，请稍后重试") from exc
            except APIConnectionError as exc:
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                cause_type = self._cause_type(exc)
                logger.error(
                    "model_request_failed model=%s error_type=connection cause_type=%s "
                    "elapsed_ms=%.2f attempt=%d/%d",
                    self.model,
                    cause_type,
                    elapsed_ms,
                    attempt,
                    max_attempts,
                )
                raise RuntimeError("Agent模型连接失败") from exc

        if response is None:
            raise RuntimeError("Agent模型未返回响应")

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

    @staticmethod
    def _status_error_code(exc: APIStatusError) -> Optional[str]:
        body = getattr(exc, "body", None)
        if not isinstance(body, dict):
            return None
        error = body.get("error", body)
        if not isinstance(error, dict):
            return None
        value = error.get("code") or error.get("type")
        return str(value) if value else None

    @staticmethod
    def _cause_type(exc: BaseException) -> str:
        current: Optional[BaseException] = exc
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if current is not exc:
                return type(current).__name__
            current = current.__cause__ or current.__context__
        return type(exc).__name__

    @staticmethod
    def _timeout_type(exc: BaseException) -> str:
        current: Optional[BaseException] = exc
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, httpx.ReadTimeout):
                return "read"
            if isinstance(current, httpx.ConnectTimeout):
                return "connect"
            if isinstance(current, httpx.WriteTimeout):
                return "write"
            if isinstance(current, httpx.PoolTimeout):
                return "pool"
            current = current.__cause__ or current.__context__
        return "unknown"
