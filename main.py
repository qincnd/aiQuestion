# SPDX-FileCopyrightText: 2026 qincnd <qincnd@qq.com>
# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
#
# Original code created by qincnd <qincnd@qq.com>
# Modified by Xue Zicheng <xuezicheng842@outlook.com>
from __future__ import annotations

import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from automation import AnswerBot

PROJECT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR))
app = Flask(
    __name__,
    template_folder=str(RESOURCE_DIR / "templates"),
    static_folder=str(RESOURCE_DIR / "static"),
)
BASE_DIR = PROJECT_DIR
CONFIG_PATH = BASE_DIR / "config.json"
bot = AnswerBot(BASE_DIR)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify(bot.status())


@app.get("/api/config")
def get_config():
    if not CONFIG_PATH.exists():
        return jsonify({"ok": False, "error": "config.json 不存在"}), 404
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return jsonify({"ok": False, "error": f"config.json 格式错误：{exc}"}), 400
    return jsonify({"ok": True, "config": config})


@app.post("/api/config")
def save_config():
    payload = request.get_json(silent=True) or {}
    config = payload.get("config")
    if not isinstance(config, dict):
        return jsonify({"ok": False, "error": "缺少 config 对象"}), 400
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return jsonify({"ok": True, "message": "配置已保存"})


@app.post("/api/start")
def start():
    started = bot.start(CONFIG_PATH)
    if not started:
        return jsonify({"ok": False, "error": "启动失败，请检查配置"}), 409
    return jsonify({"ok": True})


@app.post("/api/stop")
def stop():
    bot.stop()
    return jsonify({"ok": True})


def open_browser() -> None:
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5050")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)