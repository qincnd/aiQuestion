# SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
# SPDX-License-Identifier: MIT
from pages.registry import register
from pages.wisdomtree import WisdomTreeReader

register(WisdomTreeReader())

# 以后新增页面：
# from pages.otherapp import OtherAppReader
# register(OtherAppReader())