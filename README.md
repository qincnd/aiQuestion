# AI 答题 · dom-tree 分支

通过 ADB 的 `uiautomator dump` 直接获取 Android 控件树，解析出题干、选项、按钮及精确坐标；由 AI 通过 function calling 自主调用工具完成读题、点击、进入下一题。**不再依赖 OCR 和截图**。

---

## 项目说明

本项目仅供学习使用，无其他用途，请勿消极学业，使用本项目产生的后果请自行承担。


## 本分支与主分支的区别

| | 主分支（main） | 本分支（dom-tree） |
|---|---|---|
| 页面识别 | 截图 + RapidOCR 文字识别 | `uiautomator dump` 控件树解析 |
| 坐标来源 | OCR 框中心点（估算） | 控件 `bounds` 中心点（系统精确值） |
| 文字来源 | OCR 识别结果（有误差） | 控件 `text` 属性（原始值） |
| 交互模式 | 本地单轮问答，AI 返回坐标 | AI function calling，多轮工具调用 |
| AI 职责 | 判断答案 + 返回点击坐标 | 自主决定读页、点击、翻页 |
| 坐标精度 | 依赖 OCR 质量 | 系统级精确 |
| 依赖 | RapidOCR、Pillow、numpy | 无 OCR 依赖 |
| 适用范围 | 原生控件 + WebView 均可 | 仅限 uiautomator 可访问的页面 |

**核心差异**：主分支把 AI 当「答案判断器」，坐标由 OCR 提供；本分支把 AI 当「答题 Agent」，页面结构由控件树提供，AI 只负责决策，坐标完全由本地控制，AI 不接触坐标。

---
### 数据流

```
用户点「开始答题」
    ↓
AnswerBot 加载 config.json，连接 ADB，注册工具
    ↓
AnswerAgent 启动，system_prompt + 用户消息「开始答题」
    ↓
AI 调用 read_page 工具
    ↓
dump_and_parse：
  adb shell uiautomator dump → 拉取 XML
  → find_reader 匹配页面类型
  → reader.parse 提取题干/选项/按钮
  → 返回纯文字（不含坐标）
    ↓
AI 收到页面结构，判断答案
    ↓
AI 调用 click_option("B错")
    ↓
本地用 option_text 匹配 Option 对象，取 bounds 中心点点击
    ↓
AI 调用 click_next 或 read_page 确认
    ↓
循环直到 AI 调用 finish
```

### 可用工具

| 工具 | 参数 | 作用 |
|---|---|---|
| `read_page` | 无 | dump 控件树，返回题干、题型、选项文字、按钮文字 |
| `click_option` | `option_text` | 按选项文字匹配并点击，坐标由本地 bounds 计算 |
| `click_next` | 无 | 点击下一题/下一步/继续；检测到提交页返回 `finished=true` |
| `finish` | `reason` | 结束答题循环 |

---

## 优点

1. **文字零误差**：直接读控件 `text`，不存在 OCR 错字、漏字、拆行问题。
2. **坐标精确**：`bounds` 是系统给出的精确矩形，中心点即点击位置，不受 OCR 框偏移影响。
3. **结构清晰**：`clickable` 区分可点击项，`class` 区分按钮/文本，`package` 区分 App，解析逻辑简单可靠。
4. **AI 职责单一**：AI 只看「题干 + 选项文字」，输出答案文字，不需要理解坐标、不需要格式化输出坐标。
5. **无 OCR 依赖**：不需要 RapidOCR、Pillow、numpy，安装包更小，启动更快。
6. **可插拔页面**：新增 App 只需写一个 `PageReader` 子类，主流程一行不改。
7. **MCP 工具模式**：AI 可以主动多次读页确认状态，形成「读 → 判 → 点 → 确认」闭环，比单轮问答更鲁棒。
8. **过程可视化**：前端实时显示 AI 的工具调用轨迹（调了什么、返回什么）。

---

## 如何下载

```
git clone -b dom-tree https://github.com/qincnd/aiQuestion.git
pip install -r requirements.txt
python main.py
```

---

## 启动

### Windows

双击 `run.bat`。

### Linux / macOS

```bash
./run.sh
```

启动后自动打开 `http://127.0.0.1:5050`。

---

## 运行依赖

1. 安装 Android SDK Platform Tools，把 `adb.exe` 及其 DLL 放入 `tools/`，或把 adb 加入 PATH。
2. 手机上开启开发者选项和 USB 调试，连接后执行 `adb devices` 并在手机上授权。
3. **本分支不需要 OCR**，无需安装 RapidOCR / Tesseract / 语言包。
4. 页面填入 DeepSeek API Key。模型需要支持 function calling（`deepseek-chat` 即可）。

### 配置说明

`config.json` 分 `ai` 和 `bot` 两段，**所有字段必填，缺失直接启动失败**。

`ai` 段：

| 字段 | 说明 |
|---|---|
| `api_key` | DeepSeek API Key，必填 |
| `base_url` | API 地址，默认 `https://api.deepseek.com` |
| `model` | 模型名，需支持 function calling |
| `system_prompt` | 系统提示，必填 |
| `temperature` | 采样温度，默认 0.0 |
| `max_tool_rounds` | 单轮对话最多工具调用轮数，防止无限循环 |

`bot` 段：

| 字段 | 说明 |
|---|---|
| `answer_time` | 单题答题时间（秒） |
| `error_time` | 时间误差范围（秒） |
| `interval_min_time` / `interval_max_time` | 题目间隔（秒） |
| `page_load_timeout` | 页面加载上限（秒） |
| `screen_poll_interval` | 轮询间隔（秒） |
| `click_error_distance` | 点击随机误差半径（像素） |
| `notify_on_submit` | 到达提交页时发送 Windows 通知 |
| `adb_path` | 自定义 adb 路径，留空用 PATH |
| `device_serial` | 多设备时指定序列号 |

检测到提交/交卷页面后，程序只会停止并按开关发送 Windows 通知，**不会替用户点击提交**。

配置和 API Key 保存到项目根目录 `config.json`，API Key 为明文，请勿提交到 Git 或分享给他人。

---

## 如何适配更多的应用

1. 在 `pages/` 下新建文件，继承 `PageReader`。
2. 实现 `can_handle(xml_root)`，用 `package` 名或特定 `resource-id` 判断。
3. 实现 `parse(xml_root, screen_width, screen_height)`，返回 `PageData`。
4. 在 `pages/__init__.py` 里 `register(YourReader())`。

---

## 📝 开源许可

MIT [LICENSE](LICENSE)

## 📮 联系方式
---

作者

qincnd <qincnd@qq.com>

Xue Zicheng <xuezicheng842@outlook.com>

---