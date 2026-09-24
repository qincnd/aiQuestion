# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT

#适配(com.able.wisdomtree)
from __future__ import annotations

import re

from pages.base import Button, Option, PageData, PageReader, center_of, parse_bounds

OPTION_PATTERN = re.compile(r"^([A-Za-z])\s*[\.、\)．]?\s*(.+)$")
QUESTION_TYPE_WORDS = ("判断题", "单选题", "多选题", "不定项")
BUTTON_WORDS = ("下一题", "上一题", "提交", "交卷", "完成", "答题卡", "继续")
PACKAGE_NAME = "com.able.wisdomtree"


class WisdomTreeReader(PageReader):
    name = "wisdomtree_quiz"

    def can_handle(self, xml_root) -> bool:
        for node in xml_root.iter("node"):
            if node.get("package") == PACKAGE_NAME:
                return True
        return False

    def parse(self, xml_root, screen_width: int, screen_height: int) -> PageData:
        page = PageData(
            page_type=self.name,
            screen_width=screen_width,
            screen_height=screen_height,
        )

        clickable_nodes: list[dict] = []
        text_nodes: list[dict] = []
        raw_lines: list[str] = []

        for node in xml_root.iter("node"):
            text = (node.get("text") or "").strip()
            bounds = parse_bounds(node.get("bounds", ""))
            if not bounds:
                continue
            clickable = node.get("clickable") == "true"
            cls = node.get("class", "")
            if text:
                raw_lines.append(text)
                if clickable:
                    clickable_nodes.append({"text": text, "bounds": bounds, "class": cls})
                else:
                    text_nodes.append({"text": text, "bounds": bounds, "class": cls})

        page.raw_text = "\n".join(raw_lines)

        # 题型
        for item in text_nodes:
            if any(word in item["text"] for word in QUESTION_TYPE_WORDS):
                page.question_type = item["text"]
                break

        # 选项
        for item in clickable_nodes:
            if any(word in item["text"] for word in BUTTON_WORDS):
                continue
            m = OPTION_PATTERN.match(item["text"])
            if not m:
                continue
            cx, cy = center_of(item["bounds"])
            page.options.append(Option(
                text=item["text"],
                x=cx,
                y=cy,
                raw_id=m.group(1),
            ))

        # 按钮
        for item in clickable_nodes:
            if any(word in item["text"] for word in BUTTON_WORDS):
                cx, cy = center_of(item["bounds"])
                page.buttons.append(Button(text=item["text"], x=cx, y=cy))

        # 题干
        option_top = min((opt.y for opt in page.options), default=screen_height)
        question_parts: list[tuple[int, str]] = []
        for item in text_nodes:
            if item["class"] != "android.widget.TextView":
                continue
            if any(word in item["text"] for word in QUESTION_TYPE_WORDS):
                continue
            if any(word in item["text"] for word in BUTTON_WORDS):
                continue
            if re.fullmatch(r"[\d/]+", item["text"]):
                continue
            if item["bounds"][1] < option_top:
                question_parts.append((item["bounds"][1], item["text"]))
        question_parts.sort(key=lambda x: x[0])
        page.question = " ".join(text for _, text in question_parts)

        return page