# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

