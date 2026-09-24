# SPDX-FileCopyrightText: 2026 qincnd <qincnd@qq.com>
# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
#
# Original code created by qincnd <qincnd@qq.com>
# Modified by Xue Zicheng <xuezicheng842@outlook.com>
from __future__ import annotations

import json
import math
import random
import threading
from pathlib import Path
from typing import Any

import pages  # noqa: F401
from agent import AnswerAgent
from config_loader import load_config
from pages.base import PageData
from pages.loader import dump_and_parse


class AnswerBot:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "running": False,
            "message": "等待开始",
            "last_screen_text": "",
            "last_answer": "",
            "ai_log": [],
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _set_state(self, **values: Any) -> None:
        with self._lock:
            self._state.update(values)

    def _push_log(self, event: dict) -> None:
        with self._lock:
            log = list(self._state.get("ai_log", []))
            log.append(event)
            self._state["ai_log"] = log[-80:]

    def start(self, config_path: Path) -> bool:
        with self._lock:
            if self._state["running"]:
                return False
            self._state.update(running=True, message="正在加载配置...", last_answer="", ai_log=[])

        try:
            config = load_config(config_path)
        except Exception as exc:
            self._set_state(running=False, message=f"配置错误：{exc}")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self._set_state(message="正在停止...")

    def _run(self, config: dict[str, Any]) -> None:
        try:
            bot_cfg = config["bot"]
            ai_cfg = config["ai"]

            adb_path = bot_cfg["adb_path"]
            bundled = self.project_dir / "tools" / "adb.exe"
            if not adb_path and bundled.exists():
                adb_path = str(bundled)

            adb = AdbClient(adb_path, bot_cfg["device_serial"])
            adb.ensure_device()
            screen_w, screen_h = adb.screen_size()

            agent = AnswerAgent(ai_cfg)
            self._register_tools(agent, adb, screen_w, screen_h, bot_cfg)
            self._set_state(message="已连接设备，AI 开始答题")

            final_text = agent.run_turn(
                "开始答题。请先调用 read_page 查看当前页面，然后作答。",
                on_event=self._push_log,
            )
            self._set_state(message=f"答题结束：{final_text}", running=False)
        except Exception as exc:
            self._set_state(message=f"错误：{exc}", running=False)

    def _register_tools(self, agent, adb, screen_w, screen_h, bot_cfg):
        state = {"last_page": None}

        def read_page() -> dict[str, Any]:
            page = dump_and_parse(adb, screen_w, screen_h)
            if page is None:
                return {"error": "当前页面无法识别"}
            state["last_page"] = page
            self._set_state(last_screen_text=page.raw_text, message="AI 正在阅读页面")
            return {
                "question_type": page.question_type,
                "question": page.question,
                "options": [opt.text for opt in page.options],
                "buttons": [btn.text for btn in page.buttons],
            }

        def click_option(option_text: str) -> dict[str, Any]:
            page: PageData | None = state["last_page"]
            if page is None:
                return {"error": "请先调用 read_page"}
            target = _match_option(page, option_text)
            if target is None:
                return {"error": f"未找到选项：{option_text}", "available": [o.text for o in page.options]}
            adb.tap_with_error(target.x, target.y, bot_cfg["click_error_distance"])
            self._set_state(message=f"AI 点击了：{target.text}")
            return {"ok": True, "clicked": target.text}

        def click_next() -> dict[str, Any]:
            page = dump_and_parse(adb, screen_w, screen_h)
            if page is None:
                return {"error": "当前页面无法识别"}
            finish_words = ("提交", "交卷", "完成", "结束")
            for btn in page.buttons:
                if any(w in btn.text for w in finish_words):
                    return {"ok": True, "button": btn.text, "finished": True}
            for btn in page.buttons:
                if any(w in btn.text for w in ("下一题", "下一步", "继续")):
                    adb.tap_with_error(btn.x, btn.y, 0)
                    self._set_state(message=f"AI 点击了：{btn.text}")
                    return {"ok": True, "button": btn.text, "finished": False}
            return {"error": "未找到下一题或提交按钮"}

        def finish(reason: str = "") -> dict[str, Any]:
            self._set_state(message=f"AI 结束答题：{reason}")
            self._stop_event.set()
            return {"ok": True}

        agent.register_tool(
            name="read_page",
            description="读取当前手机页面的题目、选项和按钮。每次操作后建议重新调用以确认状态。",
            parameters={"type": "object", "properties": {}, "required": []},
            func=read_page,
        )
        agent.register_tool(
            name="click_option",
            description="点击一个选项。参数 option_text 必须与 read_page 返回的选项文字完全一致。",
            parameters={
                "type": "object",
                "properties": {
                    "option_text": {"type": "string", "description": "要点击的选项文字"}
                },
                "required": ["option_text"],
            },
            func=click_option,
        )
        agent.register_tool(
            name="click_next",
            description="点击下一题按钮。如果当前页面是提交/交卷页，返回 finished=true，不再点击。",
            parameters={"type": "object", "properties": {}, "required": []},
            func=click_next,
        )
        agent.register_tool(
            name="finish",
            description="结束答题。当所有题目完成、或无法继续时调用。",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "结束原因"}
                },
                "required": [],
            },
            func=finish,
        )


def _match_option(page: PageData, text: str):
    text = text.strip()
    for opt in page.options:
        if opt.text.strip() == text:
            return opt
    for opt in page.options:
        if text in opt.text or opt.text in text:
            return opt
    return None


class AdbClient:
    def __init__(self, adb_path: str, serial: str) -> None:
        self.adb_path = adb_path
        self.serial = serial
        self._device = None

    def _get_device(self):
        if self._device is None:
            import adbutils
            import os
            if self.adb_path:
                os.environ["ADBUTILS_ADB_PATH"] = self.adb_path
            if self.serial:
                self._device = adbutils.adb.device(serial=self.serial)
            else:
                self._device = adbutils.adb.device()
        return self._device

    def ensure_device(self) -> None:
        if self._get_device() is None:
            raise RuntimeError("未找到已授权的 ADB 手机，请检查 USB 调试和 adb 路径")

    def shell(self, command: str) -> str:
        return self._get_device().shell(command)

    def screen_size(self) -> tuple[int, int]:
        import re
        output = self.shell("wm size")
        m = re.search(r"(\d+)x(\d+)", output)
        if not m:
            raise RuntimeError(f"无法获取屏幕尺寸：{output}")
        return int(m.group(1)), int(m.group(2))

    def tap_with_error(self, x: int, y: int, distance: int) -> None:
        angle = random.uniform(0, math.tau)
        radius = random.uniform(0, distance)
        tap_x = max(0, round(x + math.cos(angle) * radius))
        tap_y = max(0, round(y + math.sin(angle) * radius))
        self._get_device().click(tap_x, tap_y)