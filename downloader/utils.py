"""
公共工具模块：视频下载功能（mp4/m3u8）、公共工具
"""
import os
import subprocess
import logging
import requests
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # 创建一个简单的占位符类
    class tqdm:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, n=1):
            pass
        def set_description(self, desc):
            pass

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
        headers: HTTP 请求头
        
    Returns:
        bool: 是否下载成功
    """
    try:
        filename = os.path.basename(output_path)
        logger.info(f"开始下载 MP4: {filename}")
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # 使用 tqdm 显示进度条
        with open(output_path, 'wb') as f:
            if TQDM_AVAILABLE and total_size > 0:
                # 有文件大小信息，显示进度条
                with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"下载 {filename[:30]}",
                    ncols=100,
                    miniters=1
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))
            else:
                # 没有文件大小信息或 tqdm 不可用，显示简单进度
                if TQDM_AVAILABLE:
                    with tqdm(
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"下载 {filename[:30]}",
                        ncols=100
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                pbar.update(len(chunk))
                else:
                    # 回退到简单日志
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                if downloaded % (chunk_size * 100) == 0:  # 每100个chunk打印一次
                                    logger.info(f"下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)")
        
        logger.info(f"MP4 下载完成: {filename}")
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
        filename = os.path.basename(output_path)
        logger.info(f"开始下载 m3u8: {filename}")
        
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
            '-progress', 'pipe:1',  # 将进度输出到 stdout
            '-loglevel', 'error',  # 只显示错误信息
            output_path
        ]
        
        logger.debug(f"执行命令: {' '.join(cmd)}")
        
        # 启动进程并实时读取进度
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 解析 ffmpeg 进度输出
        duration = None
        current_time = None
        pbar = None
        
        if TQDM_AVAILABLE:
            pbar = tqdm(
                desc=f"下载 m3u8 {filename[:30]}",
                unit='',
                ncols=100,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {elapsed}',
                total=100
            )
        
        stderr_lines = []
        try:
            # 使用线程读取 stderr（ffmpeg 将进度信息输出到 stderr）
            import threading
            import queue
            
            stderr_queue = queue.Queue()
            
            def read_stderr():
                """在单独线程中读取 stderr"""
                for line in iter(process.stderr.readline, ''):
                    if line:
                        stderr_queue.put(line)
                process.stderr.close()
            
            # 启动读取线程
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # 解析进度信息
            last_percent = -1
            while True:
                try:
                    # 从队列获取一行（带超时）
                    line = stderr_queue.get(timeout=0.5)
                    stderr_lines.append(line)
                    
                    # 解析 duration
                    if 'Duration:' in line:
                        match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                        if match:
                            hours, minutes, seconds, centiseconds = map(int, match.groups())
                            duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                            if TQDM_AVAILABLE and pbar and duration:
                                pbar.total = 100
                                pbar.unit = '%'
                    
                    # 解析当前时间
                    if 'time=' in line:
                        match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                        if match:
                            hours, minutes, seconds, centiseconds = map(int, match.groups())
                            current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                            if TQDM_AVAILABLE and pbar and duration and current_time:
                                percent = (current_time / duration) * 100
                                pbar.n = percent
                                pbar.set_postfix({"时间": f"{current_time:.1f}s/{duration:.1f}s"})
                                pbar.refresh()
                            elif not TQDM_AVAILABLE and duration and current_time:
                                percent = (current_time / duration) * 100
                                if int(percent) != last_percent and int(percent) % 10 == 0:  # 每10%打印一次
                                    logger.info(f"下载进度: {percent:.1f}% ({current_time:.1f}s/{duration:.1f}s)")
                                    last_percent = int(percent)
                
                except queue.Empty:
                    # 检查进程是否完成
                    if process.poll() is not None:
                        break
                    continue
            
            # 等待线程完成
            stderr_thread.join(timeout=1)
            
            # 读取剩余输出
            while not stderr_queue.empty():
                try:
                    line = stderr_queue.get_nowait()
                    stderr_lines.append(line)
                except queue.Empty:
                    break
            
            # 等待进程完成
            returncode = process.wait()
            
            if TQDM_AVAILABLE and pbar:
                pbar.n = 100
                pbar.refresh()
                pbar.close()
            
            if returncode == 0:
                logger.info(f"m3u8 下载完成: {filename}")
                return True
            else:
                stderr_output = ''.join(stderr_lines)
                logger.error(f"ffmpeg 执行失败: {stderr_output[-500:]}")  # 只显示最后500字符
                return False
                
        except Exception as e:
            if process.poll() is None:
                process.kill()
            if TQDM_AVAILABLE and pbar:
                pbar.close()
            logger.error(f"下载过程中出错: {e}")
            raise e
            
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
            # 确保 m3u8 输出为 .mp4 格式
            if output_path.endswith('.m3u8'):
                output_path = os.path.splitext(output_path)[0] + '.mp4'
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
    """
    安全删除文件
    
    Args:
        path: 文件路径
    """
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.info(f"已删除文件: {os.path.basename(path)}")
        elif path:
            logger.debug(f"文件不存在，跳过删除: {os.path.basename(path)}")
    except Exception as err:
        logger.warning(f"删除文件失败 {os.path.basename(path)}: {err}")


def merge_ts_files(ts_files: List[str], output_path: str) -> bool:
    """
    使用 ffmpeg 合并多个 .ts 文件
    
    Args:
        ts_files: .ts 文件路径列表（已排序）
        output_path: 输出文件路径
        
    Returns:
        bool: 是否合并成功
    """
    if not ts_files:
        return False
    
    if not check_ffmpeg_available():
        logger.error("ffmpeg 不可用，无法合并 .ts 文件")
        return False
    
    try:
        logger.info(f"开始合并 {len(ts_files)} 个 .ts 文件 → {output_path}")
        
        # 创建临时文件列表用于 ffmpeg concat demuxer
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for ts_file in ts_files:
                # 使用绝对路径，避免相对路径问题
                abs_path = os.path.abspath(ts_file)
                f.write(f"file '{abs_path}'\n")
            concat_list_path = f.name
        
        try:
            # 使用 ffmpeg concat demuxer 合并
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
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
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f".ts 文件合并完成: {output_path}")
                return True
            else:
                logger.error(f"ffmpeg 合并失败: {result.stderr}")
                return False
        finally:
            # 清理临时文件
            try:
                os.remove(concat_list_path)
            except Exception:
                pass
                
    except subprocess.TimeoutExpired:
        logger.error("合并 .ts 文件超时")
        return False
    except Exception as e:
        logger.error(f"合并 .ts 文件失败: {e}")
        return False


def detect_and_merge_ts_files(downloaded_files: List[str], output_dir: str) -> List[str]:
    """
    检测下载的 .ts 文件并合并为完整视频
    
    Args:
        downloaded_files: 下载得到的文件路径列表
        output_dir: 输出目录
        
    Returns:
        List[str]: 合并后的文件路径列表
    """
    if not downloaded_files:
        return []
    
    # 筛选出 .ts 文件
    ts_files = [f for f in downloaded_files if f.endswith('.ts')]
    if len(ts_files) < 2:
        # 少于2个 .ts 文件，不需要合并
        return []
    
    logger.info(f"检测到 {len(ts_files)} 个 .ts 文件，开始分组合并...")
    
    # 按文件名分组 .ts 文件
    # 例如: index0.ts, index1.ts, index2.ts 应该合并
    # 或者: index_50.ts, index_51.ts, index_52.ts 应该合并
    ts_groups = _group_ts_files(ts_files)
    
    if not ts_groups:
        logger.debug("未能识别 .ts 文件分组模式")
        return []
    
    merged_files = []
    for group_name, group_files in ts_groups.items():
        if len(group_files) < 2:
            continue
        
        # 排序文件（按数字顺序）
        sorted_files = _sort_ts_files(group_files)
        
        # 生成输出文件名
        output_filename = _generate_merged_filename(group_name, output_dir)
        output_path = os.path.join(output_dir, output_filename)
        
        # 合并文件
        if merge_ts_files(sorted_files, output_path):
            merged_files.append(output_path)
            logger.info(f"合并成功，开始删除 {len(sorted_files)} 个原始 .ts 文件...")
            # 删除原始 .ts 文件
            deleted_count = 0
            for ts_file in sorted_files:
                if os.path.exists(ts_file):
                    _delete_file_safely(ts_file)
                    deleted_count += 1
            logger.info(f"已合并 {len(sorted_files)} 个 .ts 文件为: {os.path.basename(output_path)}，已删除 {deleted_count} 个原始文件")
        else:
            logger.warning(f"合并失败，保留原始 .ts 文件: {group_name}")
    
    if merged_files:
        logger.info(f"成功合并 {len(merged_files)} 组 .ts 文件")
    
    return merged_files


def _group_ts_files(ts_files: List[str]) -> Dict[str, List[str]]:
    """
    将 .ts 文件按命名模式分组
    
    Args:
        ts_files: .ts 文件路径列表
        
    Returns:
        Dict[str, List[str]]: 分组后的文件，key 为组名，value 为文件列表
    """
    import re
    groups: Dict[str, List[str]] = {}
    
    for ts_file in ts_files:
        filename = os.path.basename(ts_file)
        name_without_ext = os.path.splitext(filename)[0]
        
        # 模式1: index0_2, index1_4 (下载时添加了索引后缀)
        # 匹配: base_name + segment_number + _ + download_index
        # 例如: index0_2 -> base: index, segment: 0
        match1 = re.match(r'^(.+?)(\d+)_\d+$', name_without_ext)
        if match1:
            base_name = match1.group(1)
            groups.setdefault(base_name, []).append(ts_file)
            continue
        
        # 模式2: index0, index1, index2 (数字在末尾，无下载索引)
        match2 = re.match(r'^(.+?)(\d+)$', name_without_ext)
        if match2:
            base_name = match2.group(1)
            groups.setdefault(base_name, []).append(ts_file)
            continue
        
        # 模式3: index_50_2, index_51_4 (下划线分隔 + 下载索引)
        match3 = re.match(r'^(.+?)_(\d+)_\d+$', name_without_ext)
        if match3:
            base_name = match3.group(1)
            groups.setdefault(base_name, []).append(ts_file)
            continue
        
        # 模式4: index_50, index_51, index_52 (下划线分隔，无下载索引)
        match4 = re.match(r'^(.+?)_(\d+)$', name_without_ext)
        if match4:
            base_name = match4.group(1)
            groups.setdefault(base_name, []).append(ts_file)
            continue
        
        # 模式5: 如果无法匹配，尝试提取公共前缀
        # 移除下载索引后缀（最后一个下划线和数字）
        fallback_name = re.sub(r'_\d+$', '', name_without_ext)
        if fallback_name != name_without_ext:
            groups.setdefault(fallback_name, []).append(ts_file)
        else:
            # 最后的后备方案：使用默认组
            if 'default' not in groups:
                groups['default'] = []
            groups['default'].append(ts_file)
    
    # 过滤掉只有1个文件的组
    return {k: v for k, v in groups.items() if len(v) >= 2}


def _sort_ts_files(ts_files: List[str]) -> List[str]:
    """
    按数字顺序排序 .ts 文件
    
    Args:
        ts_files: .ts 文件路径列表
        
    Returns:
        List[str]: 排序后的文件路径列表
    """
    import re
    
    def extract_number(filepath: str) -> int:
        """从文件路径中提取片段序号用于排序（忽略下载索引）"""
        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        
        # 模式1: index0_2 -> 提取 segment number (0)，忽略下载索引 (2)
        match = re.match(r'^.+?(\d+)_\d+$', name_without_ext)
        if match:
            return int(match.group(1))
        
        # 模式2: index_50_2 -> 提取 segment number (50)，忽略下载索引 (2)
        match = re.match(r'^.+?_(\d+)_\d+$', name_without_ext)
        if match:
            return int(match.group(1))
        
        # 模式3: index0 -> 提取末尾数字 (0)
        match = re.search(r'(\d+)$', name_without_ext)
        if match:
            return int(match.group(1))
        
        # 模式4: index_50 -> 提取下划线后的数字 (50)
        match = re.search(r'_(\d+)$', name_without_ext)
        if match:
            return int(match.group(1))
        
        # 如果无法提取，返回0
        return 0
    
    return sorted(ts_files, key=extract_number)


def _generate_merged_filename(group_name: str, output_dir: str) -> str:
    """
    生成合并后的文件名
    
    Args:
        group_name: 组名（例如 "index"）
        output_dir: 输出目录
        
    Returns:
        str: 文件名
    """
    # 清理组名，移除特殊字符
    clean_name = group_name.strip('_-').replace('_', '-')
    if not clean_name:
        clean_name = "merged"
    
    output_filename = f"{clean_name}_merged.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    # 如果文件已存在，添加序号
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name}_merged_{counter}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        counter += 1
    
    return output_filename

