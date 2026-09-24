# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Option:
    text: str
    x: int
    y: int
    raw_id: str = ""


@dataclass
class Button:
    text: str
    x: int
    y: int


@dataclass
class PageData:
    page_type: str = "unknown"
    question: str = ""
    question_type: str = ""
    options: list[Option] = field(default_factory=list)
    buttons: list[Button] = field(default_factory=list)
    screen_width: int = 0
    screen_height: int = 0
    raw_text: str = ""

    def signature(self) -> str:
        parts = [self.question, self.question_type]
        parts += [opt.text for opt in self.options]
        parts += [btn.text for btn in self.buttons]
        return "|".join(p for p in parts if p)


class PageReader:
    name: str = "base"

    def can_handle(self, xml_root) -> bool:
        raise NotImplementedError

    def parse(self, xml_root, screen_width: int, screen_height: int) -> PageData:
        raise NotImplementedError


def parse_bounds(bounds_str: str) -> tuple[int, int, int, int] | None:
    import re
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
    if not m:
        return None
    return tuple(map(int, m.groups()))


def center_of(bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = bounds
    return (x1 + x2) // 2, (y1 + y2) // 2