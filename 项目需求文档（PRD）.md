项目名称：VideoCollector — 通用视频下载工具（支持 Bilibili、中国抖音、常见视频网站）
目标：实现一个自动化视频下载工具，支持两种下载模式：Playwright 无头浏览器模式、浏览器脚本提取模式。

🔧 一、总体目标

开发一个跨平台（macOS / Windows / Linux）的视频下载工具，可从不提供下载功能的网站（例如 Bilibili、抖音网页端、一般视频网站）自动分析出视频流 URL，并下载为本地文件。

程序提供 两种模式：

方案 A：Playwright 无头浏览器模式
自动打开网页 → 监听网络请求 → 匹配视频流链接（m3u8/mp4）→ 下载并合并。

方案 B：浏览器 Console 脚本模式
用户 在浏览器 Console 中粘贴 JS 脚本 → 提取该页面加载的 m3u8/mp4 链接 → 把 JSON 复制到 Python CLI → 下载。

工具需提供一个统一的 CLI 接口，并在 README 中说明使用方法。

📁 二、项目目录结构（Cursor 必须创建）
video_collector/
│
├── main.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
│
├── downloader/
│   ├── __init__.py
│   ├── headless_browser_mode.py
│   ├── browser_script_mode.py
│   ├── utils.py   # 下载功能（mp4/m3u8）、公共工具
│
├── assets/
│   └── browser_snippets/
│         └── extract_video_urls.js
│
└── logs/
    └── .gitkeep

🅰️ 三、方案 A：Playwright 无头浏览器模式

模块位置：

downloader/headless_browser_mode.py

1. 功能目标

启动 Playwright（Chromium/Firefox/Webkit）

自动打开网页 URL

监听所有 network response

自动过滤：

*.m3u8

*.mp4

Content-Type 包含 "video"

自动识别单视频/多视频情况

自动下载 & 合并（m3u8 → ffmpeg）

2. 必须实现的类与接口
class HeadlessBrowserDownloader:
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """初始化 Playwright 浏览器下载器"""

    def collect_video_urls(self, url: str, timeout: int = 30000) -> List[str]:
        """打开网页，监听网络，收集视频 URL 列表"""

    def download_videos(self, video_urls: List[str], output_dir: str) -> None:
        """根据 URL 列表下载视频"""

    def run(self, url: str, output_dir: str) -> None:
        """
        一键完成：
        1. 启动浏览器 + 收集 URL
        2. 下载视频
        """

3. Playwright 监听逻辑

监听 response：

page.on("response", handle_response)


匹配规则：

response.url 包含 .m3u8 或 .mp4

response.header 的 content-type 包含 video

4. 下载逻辑必须满足

mp4 → 直接 requests 分块下载

m3u8 → 通过 ffmpeg：

ffmpeg -y -i <m3u8_url> -c copy output.mp4


异常捕获，不影响其它 URL

🅱️ 四、方案 B：浏览器脚本模式
目录位置：
assets/browser_snippets/extract_video_urls.js
downloader/browser_script_mode.py

B.1 浏览器 Console 脚本（Cursor 必须创建 JS 文件）

文件：assets/browser_snippets/extract_video_urls.js

内容要求：

扫描 performance.getEntriesByType('resource')

自动过滤 m3u8/mp4/webm

输出一个 JSON 包含：

{
  "videoUrls": ["...","..."]
}


示例脚本：

(function () {
  function isVideoUrl(url) {
    if (!url) return false;
    const lower = url.toLowerCase();
    return lower.includes(".m3u8") || lower.includes(".mp4") || lower.includes(".webm");
  }

  const resources = performance.getEntriesByType("resource");
  const videoUrls = [];

  resources.forEach((res) => {
    const url = res.name;
    if (isVideoUrl(url) && !videoUrls.includes(url)) {
      videoUrls.push(url);
    }
  });

  console.log("Detected video URLs:");
  console.log(videoUrls);

  console.log("JSON (copy this):");
  console.log(JSON.stringify({ videoUrls }, null, 2));
})();

B.2 Python 端处理逻辑

文件：
downloader/browser_script_mode.py

必须实现：

def parse_video_urls_from_input(user_input: str) -> List[str]:
    """
    自动兼容用户粘贴：
    1. JSON: {"videoUrls": [...]}
    2. URL 列表（每行一个）
    """

def download_videos_from_urls(video_urls: List[str], output_dir: str) -> None:
    """复用方案 A 的下载工具"""

📝 五、main.py CLI 设计

CLI 要求：

python main.py --mode headless --url https://xxxx --output-dir ./downloads
python main.py --mode browser_script --output-dir ./downloads


模式说明：

headless：方案 A

browser_script：方案 B

crawler（预留）：先留空，未来扩展

在 browser_script 模式下：

请粘贴从 Console 复制的 JSON/URL 列表：
Ctrl+D 提交

📚 六、README.md 生成要求（Cursor 自动生成）

README 必须包含：

✔ 项目简介（项目用途说明）

描述 VideoCollector 能干什么？为什么需要它？

✔ 安装环境说明

Python 3.9+

Playwright + ffmpeg

✔ 安装步骤
pip install -r requirements.txt
playwright install

✔ 使用方法

方案 A：无头浏览器模式

方案 B：浏览器脚本模式（包含 GIF/命令示例）

✔ 常见问题 FAQ

“为什么找不到视频 URL？”（网站使用 DRM）

“需要登录的网站如何处理？”（手动登录后再运行）

📜 七、CHANGELOG.md（Cursor 必须创建）

格式采用 Keep a Changelog + SemVer

示例：

# Changelog
All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-XX-XX
### Added
- 初始化项目结构
- 添加 Playwright 无头浏览器视频下载模式
- 添加浏览器脚本模式
- 添加 README 与使用指南
- 添加 JS 脚本 extract_video_urls.js

🧩 八、Coding Agent 的规则（必须遵守）

Coding agent 必须：

优先实现方案 A/B 的基础功能

使用 logging 模块记录调试信息

所有模块加上 docstring

未实现的高级功能用 TODO 注释

不做任何破解 DRM / 绕过登录 / 破解付费网站 的功能（保持合规）

代码必须可在 macOS、Windows、Linux 上运行