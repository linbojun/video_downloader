# VideoCollector — 通用视频下载工具

一个跨平台（macOS / Windows / Linux）的视频下载工具，可从不提供下载功能的网站（例如 Bilibili、抖音网页端、一般视频网站）自动分析出视频流 URL，并下载为本地文件。

## ✨ 功能特性

- 🎯 **两种下载模式**：
  - **方案 A：Playwright 无头浏览器模式** - 自动打开网页，监听网络请求，提取视频链接
  - **方案 B：浏览器脚本模式** - 在浏览器 Console 中运行脚本，提取视频链接后下载

- 📦 **支持多种视频格式**：
  - MP4 直接下载
  - M3U8 流媒体（使用 ffmpeg 合并）

- 🔄 **自动合并音视频**：检测 DASH `.m4s`（如 Bilibili）并用 ffmpeg 合并为 MP4，成功后清理原始分片
- 🌐 **跨平台支持**：macOS、Windows、Linux

- 🔧 **易于使用**：简单的 CLI 接口

## 📋 环境要求

- **Python**: 3.8 或更高版本（推荐 3.10+）
- **PyPI 依赖**：`playwright`、`requests`
  - `pip install -r requirements.txt` 会一次性安装
- **Playwright**: 通过 `pip install playwright` 安装
- **ffmpeg**: 用于处理 M3U8 流媒体（需要单独安装）

### 检查 Python 版本

```bash
python --version  # 或 python3 --version
```

### 安装 ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
下载并安装 [ffmpeg](https://ffmpeg.org/download.html)，确保添加到 PATH

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## 🚀 安装步骤

1. **克隆或下载项目**

```bash
cd video_downloader
```

2. **创建虚拟环境（推荐）**

```bash
# macOS/Linux
python3 -m venv venv

# Windows
python -m venv venv
```

3. **激活虚拟环境**

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

激活后，命令行提示符前会显示 `(venv)`。

4. **安装 Python 依赖**

```bash
pip install -r requirements.txt
```

或使用 pip3：

```bash
pip3 install -r requirements.txt
```

5. **安装 Playwright 浏览器**

```bash
playwright install
```

或指定浏览器：

```bash
playwright install chromium  # 推荐
playwright install firefox
playwright install webkit
```

**注意**：如果使用虚拟环境，请确保在激活虚拟环境后再运行 `playwright install`。

### 退出虚拟环境

```bash
deactivate
```

## 📖 使用方法

### 方案 A：无头浏览器模式

自动打开网页，监听网络请求，提取并下载视频。

#### 基本用法

**如果使用虚拟环境，请先激活：**

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

然后运行：

```bash
python main.py --mode headless --url <视频网页URL> --output-dir ./downloads
```

#### 示例

```bash
# 下载 Bilibili 视频
python main.py --mode headless --url https://www.bilibili.com/video/BVxxxxx --output-dir ./downloads

# 强制使用已安装的 Chrome（解决 HTML5 播放器兼容问题）
python main.py --mode headless --url https://www.bilibili.com/video/BVxxxxx --output-dir ./downloads --browser-channel chrome

# 复用当前 Chrome 配置（沿用 Widevine/登录状态）
python main.py --mode headless --url https://www.bilibili.com/video/BVxxxxx --output-dir ./downloads --browser-channel chrome --user-data-dir "~/Library/Application Support/Google/Chrome/Default"

> 提示：Chromium 模式默认注入 Anti-automation Stealth 补丁（伪装 `navigator.webdriver`、`plugins`、`sec-ch-ua` 等），帮助绕过 Bilibili 对无头浏览器的卡 loading 检测。若页面仍然停留在“加载中”，请配合 `--no-headless`、`--browser-channel chrome` 并复用本机浏览器配置（`--user-data-dir`），确保 Widevine 模块及 Cookies 已加载。

# 使用 Firefox 浏览器
python main.py --mode headless --url <URL> --output-dir ./downloads --browser-type firefox

# 显示浏览器窗口（调试用）
python main.py --mode headless --url <URL> --output-dir ./downloads --no-headless
```

#### Bilibili 实战示例（macOS + Chrome Profile 1）

以下命令在 `zsh` 中实测通过，针对 Bilibili BV 号 `BV1FYtHzEEAF`，复用本机 Chrome「Profile 1」并强制开启有头模式，确保 Widevine、Cookies 及登录态全部可用：

```bash
python main.py --mode headless \
  --url "https://www.bilibili.com/video/BV1FYtHzEEAF" \
  --browser-channel chrome \
  --user-data-dir "/Users/bojun/Library/Application Support/Google/Chrome/Profile 1" \
  --no-headless
```

- `--browser-channel chrome`：调用系统已安装的稳定版 Chrome，避免 B 站检测出精简版 Chromium 缺少解码器。
- `--user-data-dir "/Users/bojun/Library/Application Support/Google/Chrome/Profile 1"`：复用本机 Profile 1（包含 Widevine 模块、登录态、Cookies）。
- `--no-headless`：调试期间显示真实浏览器窗口，可手动完成登录或验证播放器状态。
- 若页面长时间 Loading，可在执行前关闭所有已打开的 Chrome 窗口，确保 Playwright 得以独占该用户目录。

#### 抖音网页端示例（需要可见浏览器）

抖音通常要求登录并依赖可见播放界面，下方命令展示如何在 `zsh` 中抓取作品 `7558494983238536490` 的直链，运行后可在浏览器里完成扫码/短信登录：

```bash
python main.py --mode headless \
  --url https://www.douyin.com/video/7558494983238536490 \
  --output-dir ./downloads \
  --no-headless
```

- Douyin 为动态渲染页面，`--no-headless` 可避免人机校验失败，同时方便观察播放状态。
- 若页面提示“当前地区无法观看”，可在同一窗口内手动切换账号或开启代理，程序会在后台继续监听请求。
- 运行完成后，音视频分轨将自动合并成单个 MP4 文件，输出在 `./downloads` 目录。

#### 参数说明

- `--mode headless`: 使用无头浏览器模式
- `--url`: 目标视频网页的 URL（必需）
- `--output-dir`: 输出目录（默认: `./downloads`）
- `--headless`: 使用无头模式（默认: True）
- `--no-headless`: 显示浏览器窗口
- `--browser-type`: 浏览器类型 (`chromium`, `firefox`, `webkit`，默认: `chromium`)
- `--browser-channel`: Playwright 浏览器通道，仅对 `chromium` 生效（示例：`chrome`, `chrome-beta`, `msedge`）
- `--user-data-dir`: 复用已有浏览器用户数据目录（仅 `chromium` 支持，如 `~/Library/Application Support/Google/Chrome/Default`）。若同时指定 `--browser-channel chrome` 与 `--no-headless` 且未填写该参数，程序会默认使用 `/Users/bojun/Library/Application Support/Google/Chrome/Profile 1`
- `--timeout`: 超时时间，单位毫秒（默认: 90000）

### 方案 B：浏览器脚本模式

在浏览器 Console 中运行脚本提取视频 URL，然后通过 Python CLI 下载。

#### 步骤 1：在浏览器中提取视频 URL

1. 打开目标视频网页（例如 Bilibili、抖音等）
2. 按 `F12` 打开开发者工具
3. 切换到 **Console** 标签
4. 打开文件 `assets/browser_snippets/extract_video_urls.js`，复制全部内容
5. 粘贴到 Console 中并回车
6. 复制输出的 JSON 内容

#### 步骤 2：使用 Python CLI 下载

**如果使用虚拟环境，请先激活：**

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

然后运行：

```bash
python main.py --mode browser_script --output-dir ./downloads
```

然后：
1. 粘贴从 Console 复制的 JSON 或 URL 列表
2. 按 `Ctrl+D` (Mac/Linux) 或 `Ctrl+Z` (Windows) 提交
3. 确认下载

#### 输入格式支持

**格式 1：JSON**
```json
{
  "videoUrls": [
    "https://example.com/video1.m3u8",
    "https://example.com/video2.mp4"
  ]
}
```

**格式 2：URL 列表（每行一个）**
```
https://example.com/video1.m3u8
https://example.com/video2.mp4
```

## 📁 项目结构

```
video_downloader/
│
├── main.py                    # CLI 入口文件
├── requirements.txt           # Python 依赖
├── README.md                  # 使用文档
├── CHANGELOG.md               # 变更日志
├── .gitignore                 # Git 忽略文件
├── venv/                      # 虚拟环境目录（不提交到 Git）
│
├── downloader/
│   ├── __init__.py
│   ├── headless_browser_mode.py  # 方案 A：无头浏览器模式
│   ├── browser_script_mode.py    # 方案 B：浏览器脚本模式
│   └── utils.py                   # 下载功能（mp4/m3u8）、公共工具
│
├── assets/
│   └── browser_snippets/
│         └── extract_video_urls.js  # 浏览器 Console 脚本
│
└── logs/
    └── .gitkeep
```

## ❓ 常见问题 FAQ

### Q: 为什么找不到视频 URL？

**A:** 可能的原因：

1. **网站使用 DRM 保护**：某些网站（如 Netflix、Disney+）使用 DRM 加密，无法直接提取视频 URL
2. **需要登录**：某些视频需要登录后才能访问
3. **动态加载**：视频可能通过 JavaScript 动态加载，需要等待页面完全加载

**解决方案：**
- 尝试使用 `--no-headless` 模式，手动登录后再运行
- 等待视频开始播放后再提取 URL
- 检查浏览器 Network 标签中的视频请求


### Q: Bilibili 提示“您的浏览器不支持 HTML5 播放器”？

**A:** Playwright 自带的 Chromium 精简了 Google 的专有编解码器（H.264/AAC）和 Widevine DRM，Bilibili 会因此拒绝播放。解决方法：

- 安装官方 Chrome / Edge 浏览器（大多数系统已自带）
- 启动命令中追加 `--browser-channel chrome`（或在 Windows 上使用 `--browser-channel msedge`），强制 Playwright 使用真实浏览器进程
- 项目默认会在 Chromium 模式下注入 Stealth 补丁（伪装 `navigator.webdriver`、`permissions.query` 等），避免播放器识别出自动化脚本
- 如仍有问题：
  - 关闭本机已打开的 Chrome 窗口
  - 指定 `--user-data-dir` 为本机真实配置，确保 Widevine 与 Cookies 得以复用。常见路径：
    - **macOS:** `~/Library/Application Support/Google/Chrome/Default`
    - **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\Default`
    - **Linux:** `~/.config/google-chrome/Default`
  - 配合 `--no-headless` 手动登录并等待视频加载

### Q: 需要登录的网站如何处理？

**A:** 
1. 使用 `--no-headless` 模式显示浏览器窗口
2. 在浏览器中手动登录
3. 等待视频加载完成
4. 程序会自动提取视频 URL

### Q: ffmpeg 未找到怎么办？

**A:** 
- 确保已安装 ffmpeg 并添加到系统 PATH
- 检查安装：`ffmpeg -version`
- 参考上面的"安装 ffmpeg"部分

### Q: 下载的 M3U8 文件无法播放？

**A:** 
- M3U8 是流媒体播放列表，需要使用 ffmpeg 合并
- 程序会自动使用 ffmpeg 处理 M3U8 文件
- 若是 Bilibili 等 DASH `.m4s` 片段，程序会自动合并音/视频轨并删除原始分片
- 如果自动合并失败，请检查 ffmpeg 是否正确安装

### Q: 支持哪些视频网站？

**A:** 
- 理论上支持所有不加密的视频网站
- 已测试：Bilibili、抖音网页端、一般视频网站
- 不支持：使用 DRM 保护的网站（Netflix、Disney+ 等）

### Q: 下载速度慢怎么办？

**A:** 
- MP4 文件使用分块下载，速度取决于网络和服务器
- M3U8 文件需要下载所有分片，速度较慢是正常的
- 可以尝试在网络较好的环境下下载

### Q: 如何查看详细日志？

**A:** 
- 日志文件保存在 `logs/video_collector.log`
- 控制台也会输出日志信息
- 日志级别可以通过修改 `main.py` 中的 `logging.basicConfig` 调整

## 🔒 合规说明

本工具仅用于学习和个人使用。请遵守以下规则：

- ✅ 仅下载公开可访问的视频内容
- ✅ 尊重版权，不要用于商业用途
- ❌ 不做任何破解 DRM、绕过登录、破解付费网站的功能
- ❌ 不要用于下载受版权保护的内容

## 📝 开发计划

- [ ] 添加更多视频格式支持
- [ ] 优化下载速度
- [ ] 添加下载进度条
- [ ] 支持批量下载
- [ ] 添加 GUI 界面

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**注意**：使用本工具下载视频时，请确保遵守相关网站的服务条款和版权法律。

# video_downloader
