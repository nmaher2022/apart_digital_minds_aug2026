"""LangChain wrapper for OpenRouter's OpenAI-compatible endpoint."""
from __future__ import annotations

import logging
import sys
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"

BASE_URL: str = OPENROUTER_URL
API_KEY: str | None = None
STREAM: bool = False  # set True via --stream to print tokens to stderr as they arrive

JUDGE_TOKENS = 300
SHORT_ANSWER_TOKENS = 800
ROUND_TOKENS = 1200
STRATEGY_TOKENS = 1800
DEBRIEF_TOKENS = 800


class HarnessError(RuntimeError):
    pass


def _stream(llm: ChatOpenAI, messages: list) -> tuple[str, str]:
    """Returns (content, reasoning). Content tokens are printed to stderr; reasoning is not."""
    parts: list[str] = []
    reasoning_parts: list[str] = []
    for chunk in llm.stream(messages):
        reasoning = (chunk.additional_kwargs or {}).get("reasoning") or ""
        if reasoning:
            reasoning_parts.append(reasoning)
        text = chunk.content or ""
        if text:
            print(text, end="", flush=True, file=sys.stderr)
        parts.append(text)
    print(file=sys.stderr)
    return "".join(parts), "".join(reasoning_parts)


def chat(
    model: str,
    system_prompt: str,
    history: list[dict],
    user_msg: str,
    temperature: float = 0.7,
    max_tokens: int = 800,
    retries: int = 4,
) -> tuple[str, str]:
    """Returns (content, reasoning). reasoning is "" when the model emits none."""
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    for m in history:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        messages.append(cls(content=m["content"]))
    messages.append(HumanMessage(content=user_msg))

    llm = ChatOpenAI(
        model=model,
        base_url=BASE_URL,
        api_key=API_KEY or "no-key",
        temperature=temperature,
        max_tokens=max_tokens,
    )

    logger.info(">> CALL  model=%s max_tokens=%d temp=%.1f\n%s",
                model, max_tokens, temperature, user_msg)

    last_err: Exception | None = None
    for attempt in range(retries):
        t0 = time.time()
        try:
            if STREAM:
                result, reasoning = _stream(llm, messages)
            else:
                msg = llm.invoke(messages)
                result = msg.content or ""
                reasoning = (msg.additional_kwargs or {}).get("reasoning") or ""
            elapsed = time.time() - t0
            logger.info("<< RESP  [%.2fs]\n%s", elapsed, result)
            return result, reasoning
        except Exception as e:
            elapsed = time.time() - t0
            last_err = e
            logger.warning("attempt %d failed [%.2fs]: %s", attempt + 1, elapsed, e)
            if attempt < retries - 1:
                time.sleep(2**attempt)
    raise HarnessError(str(last_err)) from last_err
