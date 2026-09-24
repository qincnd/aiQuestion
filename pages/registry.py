# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pages.base import PageReader

_READERS: list[PageReader] = []


def register(reader: PageReader) -> None:
    _READERS.append(reader)


def find_reader(xml_root) -> PageReader | None:
    for reader in _READERS:
        try:
            if reader.can_handle(xml_root):
                return reader
        except Exception:
            continue
    return None


def all_readers() -> list[PageReader]:
    return list(_READERS)