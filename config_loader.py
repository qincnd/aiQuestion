# SPDX-FileCopyrightText: 2026 qincnd <qincnd@qq.com>
# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
#
# Original code created by qincnd <qincnd@qq.com>
# Modified by Xue Zicheng <xuezicheng842@outlook.com>
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_AI_FIELDS = (
    "api_key", "base_url", "model", "system_prompt",
    "temperature", "max_tool_rounds",
)
REQUIRED_BOT_FIELDS = (
    "answer_time", "interval_min_time", "interval_max_time", "error_time",
    "click_error_distance", "page_load_timeout", "screen_poll_interval",
    "notify_on_submit", "adb_path", "device_serial",
)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件不是合法 JSON：{exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("配置文件顶层必须是对象")
    if "ai" not in data:
        raise ValueError("配置文件缺少 ai 段")
    if "bot" not in data:
        raise ValueError("配置文件缺少 bot 段")

    ai = data["ai"]
    if not isinstance(ai, dict):
        raise ValueError("ai 段必须是对象")
    for field in REQUIRED_AI_FIELDS:
        if field not in ai:
            raise ValueError(f"ai 配置缺少字段：{field}")
    if not str(ai["api_key"]).strip():
        raise ValueError("ai.api_key 不能为空")
    if not str(ai["base_url"]).strip():
        raise ValueError("ai.base_url 不能为空")
    if not str(ai["model"]).strip():
        raise ValueError("ai.model 不能为空")
    if not str(ai["system_prompt"]).strip():
        raise ValueError("ai.system_prompt 不能为空")
    try:
        ai["temperature"] = float(ai["temperature"])
    except (TypeError, ValueError) as exc:
        raise ValueError("ai.temperature 必须是数字") from exc
    try:
        ai["max_tool_rounds"] = int(ai["max_tool_rounds"])
    except (TypeError, ValueError) as exc:
        raise ValueError("ai.max_tool_rounds 必须是整数") from exc
    if ai["max_tool_rounds"] < 1:
        raise ValueError("ai.max_tool_rounds 必须 >= 1")

    bot = data["bot"]
    if not isinstance(bot, dict):
        raise ValueError("bot 段必须是对象")
    for field in REQUIRED_BOT_FIELDS:
        if field not in bot:
            raise ValueError(f"bot 配置缺少字段：{field}")

    return data