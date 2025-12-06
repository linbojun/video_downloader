# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2025-12-06

### Added
- 自动检测并合并 HLS 视频的 .ts 片段文件
  - 当视频以多个 .ts 文件形式下载时，自动识别并合并为完整视频
  - 支持多种命名模式（index0.ts, index1.ts 或 index_50.ts, index_51.ts 等）
  - 合并成功后自动删除原始 .ts 文件
  - 使用 ffmpeg concat demuxer 进行高效合并（无需重新编码）
- **浏览器延迟关闭功能**：下载开始后，浏览器会在 30 秒后自动关闭
  - 方便用户在非无头模式下查看页面或进行调试
  - 适用于所有浏览器类型（Firefox、Chromium、Webkit）
- **下载进度显示功能**：添加实时下载进度条和百分比显示
  - MP4 文件下载：显示文件大小、下载速度、进度百分比
  - M3U8 流媒体下载：显示时间进度（已下载时间/总时长）和百分比
  - 批量下载：显示总体下载进度（已完成文件数/总文件数）
  - 使用 `tqdm` 库提供美观的进度条界面
  - 如果 `tqdm` 未安装，自动回退到文本日志模式

### Changed
- **默认浏览器改为 Firefox**：将默认浏览器类型从 Chromium 改为 Firefox

### Fixed
- 修复 m3u8 下载时输出文件扩展名问题，确保输出为 .mp4 格式而非 .m3u8 文件
- **重要修复**：当检测到 m3u8 URL 时，自动跳过下载属于同一流的 .ts 文件
  - 解决浏览器只捕获部分 .ts 片段导致合并视频不完整的问题
  - 优先使用 m3u8 下载完整视频，避免下载不完整的 .ts 片段
  - 显著减少不必要的下载和存储空间浪费

## [0.1.5] - 2025-11-29

### Added
- 当命令行同时指定 `--browser-channel chrome` 与 `--no-headless` 且未传入 `--user-data-dir` 时，自动默认到 `/Users/bojun/Library/Application Support/Google/Chrome/Profile 1`，确保 Widevine/Cookies 可用
- README 新增 Bilibili 实战命令示例，展示如何在 macOS 上复用 Chrome Profile 1
- README 新增抖音网页端示例，说明如何在可见浏览器中监听作品下载直链

## [0.1.4] - 2025-11-29

### Added
- 自动检测 DASH 音/视频 `.m4s` 片段并用 ffmpeg 合并为可播放 MP4，合并成功后自动清理原始分片
- 浏览器脚本模式与无头模式共享同一套自动合并逻辑

### Changed
- `--timeout` 默认值提升到 90s，避免 B 站页面长时间加载导致提前报错

## [0.1.3] - 2025-11-29

### Added
- 新增 `--user-data-dir`（Chromium 专用）以复用本机 Chrome/Edge 配置，确保 Widevine 与登录态可用于视频播放
- `HeadlessBrowserDownloader` 支持启动 persistent context、关闭残留进程并暴露更多 Anti-automation 伪装（`navigator.userAgentData`、WebGL、网络状态等）
- README FAQ 补充各平台用户数据目录示例及使用指引

## [0.1.2] - 2025-11-29

### Added
- Chromium 模式自动注入 Anti-automation Stealth 补丁（伪装 UA、`navigator.webdriver`、`plugins` 等）
- `HeadlessBrowserDownloader` 支持自定义 UA/Locale/Timezone，默认模拟真实 Chrome 会话，解决 Bilibili 播放器一直 Loading 的问题
- README FAQ 新增 Bilibili 调试建议

## [0.1.1] - 2025-11-29

### Added
- 支持通过 Playwright `channel` 参数调用系统已安装的 Chrome / Edge 浏览器（`--browser-channel`）
- 在 README 中记录 Bilibili HTML5 播放器提示的解决方案及使用示例

## [0.1.0] - 2025-01-XX

### Added
- 初始化项目结构
- 添加 Python 虚拟环境支持（venv）
  - 创建虚拟环境配置
  - 更新安装文档，包含虚拟环境使用说明
- 添加 Playwright 无头浏览器视频下载模式（方案 A）
  - 自动打开网页并监听网络请求
  - 自动识别并提取视频 URL（m3u8/mp4）
  - 支持 Chromium、Firefox、Webkit 浏览器
  - 支持有头/无头模式
- 添加浏览器脚本模式（方案 B）
  - 提供 JavaScript 脚本用于在浏览器 Console 中提取视频 URL
  - 支持 JSON 和 URL 列表两种输入格式
  - 交互式 CLI 界面
- 添加视频下载功能
  - MP4 文件直接下载（支持分块下载）
  - M3U8 流媒体下载（使用 ffmpeg 合并）
  - 自动识别视频格式
  - 批量下载支持
- 添加统一的 CLI 接口
  - 支持两种下载模式切换
  - 丰富的命令行参数
  - 预留 crawler 模式接口
- 添加完整的项目文档
  - README.md 使用指南
  - CHANGELOG.md 变更日志
  - 代码注释和文档字符串
- 添加日志功能
  - 文件日志（logs/video_collector.log）
  - 控制台日志输出
  - 详细的调试信息

### Technical Details
- Python 3.9+ 支持
- 跨平台支持（macOS、Windows、Linux）
- 使用 Playwright 进行浏览器自动化
- 使用 ffmpeg 处理 M3U8 流媒体
- 模块化代码结构，易于扩展

