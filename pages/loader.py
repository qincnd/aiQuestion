# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
from __future__ import annotations

import xml.etree.ElementTree as ET

from pages.base import PageData
from pages.registry import find_reader


def dump_and_parse(device, screen_width, screen_height) -> PageData | None:
    try:
        device.shell("uiautomator dump /sdcard/window_dump.xml")
        xml_text = device.shell("cat /sdcard/window_dump.xml")
    except Exception as exc:
        print(f"[dump] shell 失败: {exc}")
        return None
    if not xml_text:
        print("[dump] 内容为空")
        return None
    if "<hierarchy" not in xml_text:
        print(f"[dump] 不是 XML，前 200 字符: {xml_text[:200]}")
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"[dump] XML 解析失败: {exc}")
        return None
    reader = find_reader(root)
    if reader is None:
        print(f"[dump] 无匹配 reader，XML 前 500 字符: {xml_text[:500]}")
        return None
    page = reader.parse(root, screen_width, screen_height)
    print(f"[dump] 解析成功: 题型={page.question_type}, 选项数={len(page.options)}")
    return page