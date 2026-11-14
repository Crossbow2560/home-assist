import json
import re
from collections.abc import Iterator

import httpx

from . import config, tools

SENTENCE_END = re.compile(r"(.+?[.!?])(\s+|$)", re.S)


class Chat:
    def __init__(self):
        self.history: list[dict] = []
        self.client = httpx.Client(timeout=60)

    def reply(self, user_text: str) -> Iterator[str]:
        """Yield the spoken reply one sentence at a time.

        Device control runs first on the current sentence alone; tool results are spoken
        directly rather than sent back to the model, which at 0.8B tends to fire extra,
        unrequested calls in a follow-up round. Otherwise fall through to normal chat."""
        if results := self._run_device_pass(user_text):
            reply = " ".join(results)
            yield reply
        else:
            reply = ""
            for sentence in self._stream_chat(user_text):
                reply += sentence + " "
                yield sentence
        self.history += [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": reply.strip()},
        ]

    def _run_device_pass(self, user_text: str) -> list[str]:
        body = {
            "messages": [
                {"role": "system", "content": config.DEVICE_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "tools": tools.SCHEMAS,
            "temperature": 0.0,
            "max_tokens": 500,  # includes reasoning tokens
            "chat_template_kwargs": {"enable_thinking": True},
        }
        r = self.client.post(config.LLM_URL, json=body)
        r.raise_for_status()
        message = r.json()["choices"][0]["message"]
        results = []
        for call in message.get("tool_calls") or []:
            fn = call["function"]
            result = tools.call(fn["name"], fn["arguments"])
            print(f"  [tool] {fn['name']}({fn['arguments']}) -> {result}")
            results.append(result)
        return results

    def _stream_chat(self, user_text: str) -> Iterator[str]:
        recent = self.history[-config.MAX_HISTORY * 2 :] if config.MAX_HISTORY else []
        body = {
            "messages": [
                {"role": "system", "content": config.CHAT_PROMPT},
                *recent,
                {"role": "user", "content": user_text},
            ],
            "stream": True,
            "temperature": config.CHAT_TEMPERATURE,
            "max_tokens": 200,
            # Thinking is slow and not something to speak; chat doesn't need it.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        buf = ""
        with self.client.stream("POST", config.LLM_URL, json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                buf += json.loads(line[6:])["choices"][0]["delta"].get("content") or ""
                while m := SENTENCE_END.match(buf):
                    yield clean(m.group(1))
                    buf = buf[m.end() :]
        if tail := clean(buf):
            yield tail


def clean(text: str) -> str:
    # Strip markdown symbols the model may still emit so TTS doesn't read them.
    return re.sub(r"[*_#`>]+", "", text).strip()
