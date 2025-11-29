"""
公共工具模块：视频下载功能（mp4/m3u8）、公共工具
"""
import os
import subprocess
import logging
import requests
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_mp4(url: str, output_path: str, chunk_size: int = 8192) -> bool:
    """
    下载 MP4 视频文件
    
    Args:
        url: 视频URL
        output_path: 输出文件路径
        chunk_size: 下载块大小
        
    Returns:
        bool: 是否下载成功
    """
    try:
        logger.info(f"开始下载 MP4: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        logger.debug(f"下载进度: {percent:.1f}%")
        
        logger.info(f"MP4 下载完成: {output_path}")
        return True
    except Exception as e:
        logger.error(f"下载 MP4 失败 {url}: {e}")
        return False


def download_m3u8(url: str, output_path: str) -> bool:
    """
    使用 ffmpeg 下载并合并 m3u8 视频
    
    Args:
        url: m3u8 URL
        output_path: 输出文件路径
        
    Returns:
        bool: 是否下载成功
    """
    try:
        logger.info(f"开始下载 m3u8: {url}")
        
        # 检查 ffmpeg 是否可用
        if not check_ffmpeg_available():
            logger.error("ffmpeg 未安装或不在 PATH 中")
            return False
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # 使用 ffmpeg 下载并合并
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', url,
            '-c', 'copy',  # 直接复制流，不重新编码
            output_path
        ]
        
        logger.debug(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode == 0:
            logger.info(f"m3u8 下载完成: {output_path}")
            return True
        else:
            logger.error(f"ffmpeg 执行失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"下载 m3u8 超时: {url}")
        return False
    except Exception as e:
        logger.error(f"下载 m3u8 失败 {url}: {e}")
        return False


def check_ffmpeg_available() -> bool:
    """
    检查 ffmpeg 是否可用
    
    Returns:
        bool: ffmpeg 是否可用
    """
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=5
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_video_url(url: str) -> bool:
    """
    判断 URL 是否为视频 URL
    
    Args:
        url: 待检查的URL
        
    Returns:
        bool: 是否为视频URL
    """
    if not url:
        return False
    
    url_lower = url.lower()
    video_extensions = ['.m3u8', '.mp4', '.webm', '.flv', '.avi', '.mov']
    
    # 检查文件扩展名
    for ext in video_extensions:
        if ext in url_lower:
            return True
    
    return False


def get_video_filename(url: str, index: Optional[int] = None, default_name: str = "video") -> str:
    """
    从 URL 生成文件名
    
    Args:
        url: 视频URL
        index: 视频索引（用于多个视频时）
        default_name: 默认文件名
        
    Returns:
        str: 文件名
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # 尝试从路径提取文件名
        if path:
            filename = os.path.basename(path)
            # 移除查询参数部分
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # 如果没有扩展名，尝试从URL推断
            if not os.path.splitext(filename)[1]:
                if '.m3u8' in url.lower():
                    filename = f"{filename}.m3u8"
                elif '.mp4' in url.lower():
                    filename = f"{filename}.mp4"
            
            if filename and '.' in filename:
                if index is not None:
                    name, ext = os.path.splitext(filename)
                    return f"{name}_{index}{ext}"
                return filename
    except Exception as e:
        logger.debug(f"解析文件名失败: {e}")
    
    # 默认文件名
    if index is not None:
        return f"{default_name}_{index}.mp4"
    return f"{default_name}.mp4"


def download_video(url: str, output_dir: str, filename: Optional[str] = None, index: Optional[int] = None) -> Optional[str]:
    """
    通用视频下载函数，自动识别 mp4 或 m3u8
    
    Args:
        url: 视频URL
        output_dir: 输出目录
        filename: 指定文件名（可选）
        index: 视频索引（用于多个视频时）
        
    Returns:
        Optional[str]: 下载成功返回文件路径，失败返回 None
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        if filename is None:
            filename = get_video_filename(url, index)
        
        output_path = os.path.join(output_dir, filename)
        
        url_lower = url.lower()
        if '.m3u8' in url_lower:
            success = download_m3u8(url, output_path)
        elif '.mp4' in url_lower or url_lower.startswith('http'):
            # 假设是 mp4 或其他视频格式
            success = download_mp4(url, output_path)
        else:
            logger.warning(f"无法识别视频格式，尝试作为 MP4 下载: {url}")
            success = download_mp4(url, output_path)
        
        if success and os.path.exists(output_path):
            return output_path
        return None
        
    except Exception as e:
        logger.error(f"下载视频失败 {url}: {e}")
        return None


def download_videos(video_urls: List[str], output_dir: str) -> List[str]:
    """
    批量下载视频
    
    Args:
        video_urls: 视频URL列表
        output_dir: 输出目录
        
    Returns:
        List[str]: 成功下载的文件路径列表
    """
    downloaded_files = []
    
    for i, url in enumerate(video_urls):
        logger.info(f"下载视频 {i+1}/{len(video_urls)}: {url}")
        file_path = download_video(url, output_dir, index=i if len(video_urls) > 1 else None)
        if file_path:
            downloaded_files.append(file_path)
        else:
            logger.warning(f"跳过失败的视频: {url}")
    
    return downloaded_files

