"""
公共工具模块：视频下载功能（mp4/m3u8）、公共工具
"""
import os
import subprocess
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_mp4(
    url: str,
    output_path: str,
    chunk_size: int = 8192,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
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
        response = requests.get(url, stream=True, timeout=30, headers=headers)
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
    
    video_extensions = ['.m3u8', '.mp4', '.webm', '.flv', '.avi', '.mov', '.m4s', '.mpd']
    
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext in video_extensions:
            if path.endswith(ext):
                return True
    except Exception:
        return False
    
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


def download_video(
    url: str,
    output_dir: str,
    filename: Optional[str] = None,
    index: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
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
        parsed_path = urlparse(url).path.lower()
        binary_exts = ['.mp4', '.m4s', '.webm', '.flv', '.avi', '.mov']
        
        if '.m3u8' in url_lower:
            success = download_m3u8(url, output_path)
        elif any(parsed_path.endswith(ext) for ext in binary_exts) or url_lower.startswith('http'):
            # 假设是 mp4 或其他视频格式
            success = download_mp4(url, output_path, headers=headers)
        else:
            logger.warning(f"无法识别视频格式，尝试作为 MP4 下载: {url}")
            success = download_mp4(url, output_path, headers=headers)
        
        if success and os.path.exists(output_path):
            return output_path
        return None
        
    except Exception as e:
        logger.error(f"下载视频失败 {url}: {e}")
        return None


def download_videos(
    video_urls: List[str],
    output_dir: str,
    headers_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[str]:
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
        headers = headers_map.get(url) if headers_map else None
        file_path = download_video(
            url,
            output_dir,
            index=i if len(video_urls) > 1 else None,
            headers=headers,
        )
        if file_path:
            downloaded_files.append(file_path)
        else:
            logger.warning(f"跳过失败的视频: {url}")
    
    return downloaded_files


def auto_mux_downloads(downloaded_files: List[str], output_dir: str) -> List[str]:
    """
    自动检测并合并分离的音视频流（例如 Bilibili DASH 的 .m4s）
    
    Args:
        downloaded_files: 下载得到的原始文件路径
        output_dir: 输出目录
        
    Returns:
        List[str]: 成功合并后的文件路径列表
    """
    if len(downloaded_files) < 2:
        return []
    
    if not check_ffmpeg_available():
        logger.debug("ffmpeg 不可用，跳过自动合并")
        return []
    
    video_only: List[str] = []
    audio_only: List[str] = []
    
    for file_path in downloaded_files:
        profile = _probe_stream_profile(file_path)
        if not profile:
            continue
        video_streams, audio_streams = profile
        if video_streams > 0 and audio_streams == 0:
            video_only.append(file_path)
        elif audio_streams > 0 and video_streams == 0:
            audio_only.append(file_path)
    
    if not video_only or not audio_only:
        return []
    
    audio_map = _group_by_base(audio_only)
    muxed_files: List[str] = []
    for idx, video_path in enumerate(video_only):
        audio_path = _pop_matching_audio(audio_map, video_path)
        if not audio_path:
            logger.debug(f"未找到匹配音频，跳过: {video_path}")
            continue
        output_path = _build_mux_output_path(video_path, audio_path, output_dir, idx)
        if mux_streams(video_path, audio_path, output_path):
            muxed_files.append(output_path)
            _delete_file_safely(video_path)
            _delete_file_safely(audio_path)
    
    if muxed_files:
        logger.info(f"自动合并完成 {len(muxed_files)} 个文件")
    return muxed_files


def mux_streams(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    使用 ffmpeg 合并独立的音轨/视频轨
    """
    try:
        logger.info(f"开始合并音视频: {video_path} + {audio_path} → {output_path}")
        cmd = [
            'ffmpeg',
            '-y',
            '-loglevel', 'error',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'copy',
            output_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"合并完成: {output_path}")
            return True
        logger.error(f"合并失败: {result.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg 合并超时")
        return False
    except FileNotFoundError:
        logger.error("未找到 ffmpeg，请确认已安装并在 PATH 中")
        return False
    except Exception as err:
        logger.error(f"合并音视频失败: {err}")
        return False


def _probe_stream_profile(file_path: str) -> Optional[Tuple[int, int]]:
    """
    使用 ffprobe 检测文件内音轨/视频轨数量
    """
    if not os.path.exists(file_path):
        return None
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.debug(f"ffprobe 解析失败: {result.stderr.strip()}")
            return None
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        video_streams = sum(1 for line in lines if line == 'video')
        audio_streams = sum(1 for line in lines if line == 'audio')
        return video_streams, audio_streams
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.debug("ffprobe 不可用或执行超时，跳过流信息检测")
        return None
    except Exception as err:
        logger.debug(f"检测媒体信息失败: {err}")
        return None


def _build_mux_output_path(
    video_path: str,
    audio_path: str,
    output_dir: str,
    index: int
) -> str:
    video_base = _normalize_stem(Path(video_path).stem)
    audio_base = _normalize_stem(Path(audio_path).stem)
    base_name = _derive_common_prefix(video_base, audio_base) or "merged"
    
    candidate = Path(output_dir) / f"{base_name}.mp4"
    suffix = 1
    while candidate.exists():
        candidate = Path(output_dir) / f"{base_name}_{suffix}.mp4"
        suffix += 1
    return str(candidate)


def _normalize_stem(stem: str) -> str:
    if '_' in stem:
        stem = stem.rsplit('_', 1)[0]
    return stem.strip().strip("-_.")


def _derive_common_prefix(a: str, b: str) -> str:
    if a == b:
        return a
    prefix = os.path.commonprefix([a, b]).rstrip("-_.")
    return prefix


def _group_by_base(paths: List[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for path in paths:
        base = _normalize_stem(Path(path).stem) or Path(path).stem
        grouped.setdefault(base, []).append(path)
    return grouped


def _pop_matching_audio(audio_map: Dict[str, List[str]], video_path: str) -> Optional[str]:
    base = _normalize_stem(Path(video_path).stem)
    candidates = audio_map.get(base)
    if candidates:
        path = candidates.pop(0)
        if not candidates:
            audio_map.pop(base, None)
        return path
    # fallback to any remaining audio
    for key, values in list(audio_map.items()):
        if values:
            path = values.pop(0)
            if not values:
                audio_map.pop(key, None)
            return path
    return None


def _delete_file_safely(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.debug(f"已删除原始文件: {path}")
    except Exception as err:
        logger.debug(f"删除文件失败 {path}: {err}")

