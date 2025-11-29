"""
方案 B：浏览器脚本模式
用户 在浏览器 Console 中粘贴 JS 脚本 → 提取该页面加载的 m3u8/mp4 链接 → 把 JSON 复制到 Python CLI → 下载
"""
import json
import logging
import sys
from typing import List
from .utils import download_videos

logger = logging.getLogger(__name__)


def parse_video_urls_from_input(user_input: str) -> List[str]:
    """
    自动兼容用户粘贴：
    1. JSON: {"videoUrls": [...]}
    2. URL 列表（每行一个）
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        List[str]: 解析出的视频URL列表
    """
    video_urls = []
    
    if not user_input or not user_input.strip():
        return video_urls
    
    user_input = user_input.strip()
    
    # 尝试解析 JSON
    try:
        data = json.loads(user_input)
        if isinstance(data, dict) and "videoUrls" in data:
            video_urls = data["videoUrls"]
            if isinstance(video_urls, list):
                logger.info(f"从 JSON 解析到 {len(video_urls)} 个视频URL")
                return [url for url in video_urls if url and isinstance(url, str)]
    except json.JSONDecodeError:
        # 不是 JSON，尝试按行解析
        pass
    
    # 按行解析 URL 列表
    lines = user_input.split('\n')
    for line in lines:
        line = line.strip()
        if line and (line.startswith('http://') or line.startswith('https://')):
            video_urls.append(line)
    
    if video_urls:
        logger.info(f"从文本解析到 {len(video_urls)} 个视频URL")
    
    return video_urls


def read_user_input() -> str:
    """
    读取用户输入（支持多行，Ctrl+D 结束）
    
    Returns:
        str: 用户输入的文本
    """
    print("\n" + "=" * 60)
    print("浏览器脚本模式")
    print("=" * 60)
    print("请粘贴从浏览器 Console 复制的 JSON 或 URL 列表：")
    print("（输入完成后按 Ctrl+D (Mac/Linux) 或 Ctrl+Z (Windows) 提交）")
    print("=" * 60 + "\n")
    
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        # Ctrl+D 或 Ctrl+Z 触发
        pass
    
    return '\n'.join(lines)


def download_videos_from_urls(video_urls: List[str], output_dir: str) -> None:
    """
    复用方案 A 的下载工具下载视频
    
    Args:
        video_urls: 视频URL列表
        output_dir: 输出目录
    """
    if not video_urls:
        logger.warning("没有视频URL可下载")
        return
    
    logger.info(f"开始下载 {len(video_urls)} 个视频到: {output_dir}")
    downloaded_files = download_videos(video_urls, output_dir)
    logger.info(f"成功下载 {len(downloaded_files)} 个视频")


def run(output_dir: str) -> None:
    """
    运行浏览器脚本模式
    
    Args:
        output_dir: 输出目录
    """
    logger.info("=" * 60)
    logger.info("开始执行浏览器脚本模式")
    logger.info(f"输出目录: {output_dir}")
    logger.info("=" * 60)
    
    # 读取用户输入
    user_input = read_user_input()
    
    # 解析视频URL
    video_urls = parse_video_urls_from_input(user_input)
    
    if not video_urls:
        logger.error("未能解析到任何视频URL")
        logger.error("请确保输入格式正确：")
        logger.error("1. JSON 格式: {\"videoUrls\": [\"url1\", \"url2\"]}")
        logger.error("2. URL 列表（每行一个）")
        return
    
    # 显示解析结果
    print(f"\n解析到 {len(video_urls)} 个视频URL：")
    for i, url in enumerate(video_urls, 1):
        print(f"  {i}. {url}")
    
    # 确认下载
    print("\n是否开始下载？(y/n): ", end='', flush=True)
    try:
        confirm = input().strip().lower()
        if confirm not in ['y', 'yes', '']:
            logger.info("用户取消下载")
            return
    except (EOFError, KeyboardInterrupt):
        logger.info("用户取消下载")
        return
    
    # 下载视频
    download_videos_from_urls(video_urls, output_dir)

