# SPDX-FileCopyrightText: 2026 qincnd <qincnd@qq.com>
# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
#
# Original code created by qincnd <qincnd@qq.com>
# Modified by Xue Zicheng <xuezicheng842@outlook.com>
from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class AnswerAgent:
    def __init__(self, ai_config: dict[str, Any]) -> None:
        self.client = OpenAI(
            api_key=ai_config["api_key"],
            base_url=ai_config["base_url"],
        )
        self.model = ai_config["model"]
        self.system_prompt = ai_config["system_prompt"]
        self.temperature = ai_config["temperature"]
        self.max_tool_rounds = ai_config["max_tool_rounds"]
        self.tools: list[dict[str, Any]] = []
        self.tool_functions: dict[str, Callable] = {}
        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt}
        ]

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
    ) -> None:
        self.tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
        self.tool_functions[name] = func

    def run_turn(self, user_message: str, on_event: Callable[[dict], None] | None = None) -> str:
        """执行一轮用户输入，内部循环处理工具调用。on_event 用于把过程推给前端。"""
        def emit(event: dict) -> None:
            if on_event:
                try:
                    on_event(event)
                except Exception:
                    pass

        self.messages.append({"role": "user", "content": user_message})

        for _ in range(self.max_tool_rounds):
            params: dict[str, Any] = {
                "model": self.model,
                "messages": self.messages,
                "stream": True,
                "temperature": self.temperature,
            }
            if self.tools:
                params["tools"] = self.tools
                params["tool_choice"] = "auto"

            stream = self.client.chat.completions.create(**params)

            collected_content: list[str] = []
            collected_tool_calls: list[dict[str, Any]] = []
            finish_reason = None

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                if delta.content:
                    collected_content.append(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        while len(collected_tool_calls) <= tc.index:
                            collected_tool_calls.append({
                                "id": "",
                                "function": {"name": "", "arguments": ""},
                                "type": "function",
                            })
                        if tc.id:
                            collected_tool_calls[tc.index]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                collected_tool_calls[tc.index]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                collected_tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

            if finish_reason == "tool_calls" and collected_tool_calls:
                self.messages.append({  # type: ignore
                    "role": "assistant",
                    "content": "".join(collected_content) if collected_content else None,
                    "tool_calls": collected_tool_calls,
                })
                for tool_call in collected_tool_calls:
                    func_name = tool_call["function"]["name"]
                    raw_args = tool_call["function"]["arguments"] or "{}"
                    emit({"type": "tool_call", "name": func_name, "arguments": raw_args})
                    try:
                        func_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        content = f"Error: Invalid JSON arguments for tool '{func_name}'"
                        emit({"type": "tool_result", "name": func_name, "result": content})
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": content,
                        })
                        continue

                    if func_name not in self.tool_functions:
                        content = f"Error: Tool '{func_name}' not found."
                        emit({"type": "tool_result", "name": func_name, "result": content})
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": content,
                        })
                        continue

                    try:
                        result = self.tool_functions[func_name](**func_args)
                        content = json.dumps(result, ensure_ascii=False)
                    except Exception as exc:
                        content = f"Error executing tool '{func_name}': {exc}"
                    emit({"type": "tool_result", "name": func_name, "result": content})
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": content,
                    })
                continue

            if collected_content:
                final = "".join(collected_content)
                self.messages.append({"role": "assistant", "content": final})
                emit({"type": "assistant", "content": final})
                return final
            return ""

        return "（达到最大工具调用轮数）"