"""
方案 A：Playwright 无头浏览器模式
自动打开网页 → 监听网络请求 → 匹配视频流链接（m3u8/mp4）→ 下载并合并
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
)
from .utils import download_video, get_video_filename, is_video_url, auto_mux_downloads, detect_and_merge_ts_files

logger = logging.getLogger(__name__)

DEFAULT_CHROMIUM_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_6) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.6668.89 Safari/537.36"
)

DEFAULT_SEC_CH_UA = '"Google Chrome";v="129", "Not=A?Brand";v="24", "Chromium";v="129"'
DEFAULT_SEC_CH_UA_PLATFORM = '"macOS"'
DEFAULT_SEC_CH_UA_FULL_VERSION = '"129.0.6668.89"'
DEFAULT_SEC_CH_UA_PLATFORM_VERSION = '"13.6.6"'

STEALTH_INIT_SCRIPT = """
() => {
    const patch = () => {
        const override = (object, property, value) => {
            try {
                Object.defineProperty(object, property, {
                    get: () => value,
                    configurable: true,
                });
            } catch (err) {
                console.debug(`override ${property} failed`, err);
            }
        };

        override(navigator, 'webdriver', undefined);
        window.chrome = window.chrome || { runtime: {} };
        override(navigator, 'plugins', [1, 2, 3, 4, 5]);
        override(navigator, 'languages', ['zh-CN', 'zh', 'en']);
        override(navigator, 'hardwareConcurrency', 8);
        override(navigator, 'deviceMemory', 8);
        override(navigator, 'platform', 'MacIntel');

        if (!navigator.userAgentData) {
            const userAgentData = {
                brands: [
                    { brand: 'Google Chrome', version: '129' },
                    { brand: 'Not=A?Brand', version: '24' },
                    { brand: 'Chromium', version: '129' },
                ],
                mobile: false,
                platform: 'macOS',
                getHighEntropyValues: async (keys) => {
                    const data = {
                        platform: 'macOS',
                        platformVersion: '13.6.6',
                        architecture: 'x86',
                        model: '',
                        uaFullVersion: '129.0.6668.89',
                        bitness: '64',
                    };
                    if (!Array.isArray(keys)) {
                        return data;
                    }
                    return keys.reduce((acc, key) => {
                        acc[key] = data[key];
                        return acc;
                    }, {});
                },
            };
            override(navigator, 'userAgentData', userAgentData);
        }

        const permissions = navigator.permissions;
        if (permissions && permissions.query) {
            const originalQuery = permissions.query.bind(permissions);
            permissions.query = (parameters) => {
                if (parameters && parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission });
                }
                return originalQuery(parameters);
            };
        }

        if (!navigator.connection) {
            override(navigator, 'connection', {
                effectiveType: '4g',
                rtt: 50,
                downlink: 10,
                saveData: false,
            });
        }

        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function (parameter) {
            if (parameter === 37445) {
                return 'Apple Inc.';
            }
            if (parameter === 37446) {
                return 'Apple M2';
            }
            return getParameter.call(this, parameter);
        };
    };

    patch();
}
"""


class HeadlessBrowserDownloader:
    """Playwright 无头浏览器下载器"""
    
    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "firefox",
        browser_channel: Optional[str] = None,
        user_agent: Optional[str] = None,
        enable_stealth: bool = True,
        locale: str = "zh-CN",
        timezone_id: str = "Asia/Shanghai",
        user_data_dir: Optional[str] = None,
    ):
        """
        初始化 Playwright 浏览器下载器
        
        Args:
            headless: 是否使用无头模式
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit"，默认: "firefox")
            browser_channel: 浏览器通道 (仅对 chromium 生效，如 "chrome"、"msedge")
            user_agent: 自定义 UA
            enable_stealth: 是否开启 Anti-automation 补丁（默认开启，仅对 chromium 生效）
            locale: 浏览器语言
            timezone_id: 浏览器时区
            user_data_dir: 复用已有浏览器用户数据目录（仅对 chromium 生效，确保 Widevine/登录状态）
        """
        self.headless = headless
        self.browser_type = browser_type
        self.browser_channel = browser_channel
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_data_dir = Path(user_data_dir).expanduser() if user_data_dir else None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.video_urls: Set[str] = set()
        self.video_request_meta: Dict[str, Dict[str, str]] = {}
        self.target_url: Optional[str] = None
        self.target_origin: Optional[str] = None
        self.playwright_context_manager = None  # 用于保持 Playwright 上下文管理器打开
        self.playwright_instance = None  # 已进入的 Playwright 实例
        self.user_agent = user_agent
        self.enable_stealth = enable_stealth and browser_type == "chromium"
        if self.enable_stealth and not self.user_agent:
            self.user_agent = DEFAULT_CHROMIUM_USER_AGENT
        self.extra_http_headers: Dict[str, str] = {}
        if self.enable_stealth:
            self.extra_http_headers = {
                "sec-ch-ua": DEFAULT_SEC_CH_UA,
                "sec-ch-ua-platform": DEFAULT_SEC_CH_UA_PLATFORM,
                "sec-ch-ua-full-version": DEFAULT_SEC_CH_UA_FULL_VERSION,
                "sec-ch-ua-platform-version": DEFAULT_SEC_CH_UA_PLATFORM_VERSION,
                "sec-ch-ua-mobile": "?0",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        
    async def _handle_response(self, response):
        """
        处理网络响应，提取视频URL
        
        Args:
            response: Playwright Response 对象
        """
        try:
            url = response.url
            headers = response.headers
            
            # 检查 URL 是否包含视频扩展名
            content_type = headers.get('content-type', '').lower()
            is_media_response = any(
                keyword in content_type for keyword in ('video', 'audio')
            )
            
            if is_video_url(url) or is_media_response:
                log_prefix = (
                    f"发现媒体响应 (Content-Type: {content_type})"
                    if content_type else "发现媒体URL"
                )
                logger.info(f"{log_prefix}: {url}")
                self.video_urls.add(url)
                await self._store_response_metadata(response)
                
        except Exception as e:
            logger.debug(f"处理响应时出错: {e}")
    
    async def collect_video_urls(self, url: str, timeout: int = 90000, keep_browser_open: bool = False) -> List[str]:
        """
        打开网页，监听网络，收集视频 URL 列表
        
        Args:
            url: 目标网页URL
            timeout: 超时时间（毫秒）
            keep_browser_open: 是否保持浏览器打开（不自动关闭）
            
        Returns:
            List[str]: 收集到的视频URL列表
        """
        self.video_urls.clear()
        self.video_request_meta.clear()
        self.target_url = url
        parsed = urlparse(url)
        self.target_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
        
        try:
            if keep_browser_open and self.playwright_instance:
                # 使用已存在的 Playwright 实例
                p = self.playwright_instance
            else:
                # 创建新的 Playwright 上下文管理器
                playwright_cm = async_playwright()
                p = await playwright_cm.__aenter__()
                if keep_browser_open:
                    # 保存上下文管理器和实例以便后续清理
                    self.playwright_context_manager = playwright_cm
                    self.playwright_instance = p
            
            # 启动浏览器
            launch_kwargs = {"headless": self.headless}
            context_kwargs = self._build_context_kwargs()
            
            if self.browser_channel and self.browser_type != "chromium":
                logger.warning(
                    "browser_channel 仅对 chromium 生效，已忽略该参数"
                )
            
            if self.browser_type == "chromium":
                launch_args = self._build_launch_args()
                if launch_args:
                    existing_args = launch_kwargs.get("args", [])
                    launch_kwargs["args"] = [*existing_args, *launch_args]
                if self.browser_channel:
                    launch_kwargs["channel"] = self.browser_channel
                    logger.info(
                        f"使用浏览器通道: {self.browser_channel}"
                    )
                if self.user_data_dir:
                    logger.info(
                        f"复用用户数据目录: {self.user_data_dir}"
                    )
                    self.context = await p.chromium.launch_persistent_context(
                        str(self.user_data_dir),
                        **launch_kwargs,
                        **context_kwargs,
                    )
                    self.browser = self.context.browser
                else:
                    self.browser = await p.chromium.launch(**launch_kwargs)
                    self.context = await self.browser.new_context(**context_kwargs)
            elif self.browser_type == "firefox":
                self.browser = await p.firefox.launch(**launch_kwargs)
                self.context = await self.browser.new_context(**context_kwargs)
            elif self.browser_type == "webkit":
                self.browser = await p.webkit.launch(**launch_kwargs)
                self.context = await self.browser.new_context(**context_kwargs)
            else:
                raise ValueError(f"不支持的浏览器类型: {self.browser_type}")
            
            logger.info(f"启动浏览器: {self.browser_type} (headless={self.headless})")
            
            if self.enable_stealth:
                await self._apply_stealth_polyfills()
            self.page = await self.context.new_page()
            
            # 监听响应
            self.page.on("response", self._handle_response)
            
            logger.info(f"正在访问: {url}")
            # 访问页面
            await self.page.goto(url, wait_until="networkidle", timeout=timeout)
            
            # 等待一段时间以捕获延迟加载的视频
            logger.info("等待页面加载完成...")
            await asyncio.sleep(5)
            
            # 尝试滚动页面以触发懒加载
            try:
                await self.page.evaluate("""
                    () => {
                        window.scrollTo(0, document.body.scrollHeight);
                        return new Promise(resolve => setTimeout(resolve, 2000));
                    }
                """)
                await self.page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(2)
            except Exception as e:
                logger.debug(f"滚动页面时出错: {e}")
            
            if not keep_browser_open:
                # 自动关闭浏览器和 Playwright
                await self._cleanup_resources()
                try:
                    await playwright_cm.__aexit__(None, None, None)
                except Exception:
                    pass
                        
        except Exception as e:
            logger.error(f"收集视频URL时出错: {e}")
            if not keep_browser_open:
                await self._cleanup_resources()
                try:
                    if 'playwright_cm' in locals():
                        await playwright_cm.__aexit__(None, None, None)
                except Exception:
                    pass
        
        video_urls_list = list(self.video_urls)
        logger.info(f"共收集到 {len(video_urls_list)} 个视频URL")
        return video_urls_list

    async def _cleanup_resources(self) -> None:
        """关闭浏览器/上下文，避免残留进程"""
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            finally:
                self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            finally:
                self.browser = None
        # 关闭 Playwright 上下文管理器（如果存在）
        if self.playwright_context_manager:
            try:
                await self.playwright_context_manager.__aexit__(None, None, None)
            except Exception:
                pass
            finally:
                self.playwright_context_manager = None
                self.playwright_instance = None
    
    def _build_launch_args(self) -> List[str]:
        """构建 Chromium 启动参数，移除 --enable-automation 等标记"""
        if not self.enable_stealth:
            return []
        args = [
            "--disable-blink-features=AutomationControlled",
            "--lang=zh-CN",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
        ]
        if not self.headless:
            args.append("--start-maximized")
        return args
    
    def _build_context_kwargs(self) -> Dict[str, object]:
        """构建 BrowserContext 启动参数，模拟真实用户环境"""
        context_kwargs: Dict[str, object] = {
            "viewport": {"width": 1920, "height": 1080},
            "device_scale_factor": 1,
        }
        if self.locale:
            context_kwargs["locale"] = self.locale
        if self.timezone_id:
            context_kwargs["timezone_id"] = self.timezone_id
        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent
        if self.extra_http_headers:
            context_kwargs["extra_http_headers"] = self.extra_http_headers
        return context_kwargs
    
    async def _apply_stealth_polyfills(self) -> None:
        """注入反自动化脚本，避免触发 HTML5 播放器的 webdriver 检测"""
        if not self.context:
            return
        try:
            await self.context.add_init_script(STEALTH_INIT_SCRIPT)
            logger.debug("已注入 stealth polyfill 脚本")
        except Exception as err:
            logger.debug(f"注入 stealth 脚本失败: {err}")
    
    async def _store_response_metadata(self, response) -> None:
        """记录媒体请求所需的下载头部，确保后续直连不被 403 拒绝"""
        try:
            url = response.url
            request = response.request
            raw_headers = await request.all_headers()
            prepared = self._prepare_download_headers(raw_headers)
            self.video_request_meta[url] = prepared
        except Exception as err:
            logger.debug(f"记录请求头失败: {err}")
    
    def _prepare_download_headers(self, raw_headers: Dict[str, str]) -> Dict[str, str]:
        """清理 Playwright 请求头，仅保留下载所需字段"""
        headers: Dict[str, str] = {}
        allowed = {
            "accept",
            "accept-encoding",
            "accept-language",
            "range",
            "user-agent",
            "cookie",
            "referer",
            "origin",
            "sec-fetch-site",
            "sec-fetch-mode",
            "sec-fetch-dest",
        }
        
        for key, value in raw_headers.items():
            lower_key = key.lower()
            if lower_key in allowed and value:
                # 标准化首字母
                normalized_key = "-".join(part.capitalize() for part in lower_key.split("-"))
                headers[normalized_key] = value
        
        if self.target_url and "Referer" not in headers:
            headers["Referer"] = self.target_url
        if self.target_origin and "Origin" not in headers:
            headers["Origin"] = self.target_origin
        if "User-Agent" not in headers:
            headers["User-Agent"] = self.user_agent or DEFAULT_CHROMIUM_USER_AGENT
        else:
            headers["User-Agent"] = headers["User-Agent"] or (self.user_agent or DEFAULT_CHROMIUM_USER_AGENT)
        
        # 避免只下载首个 range 块
        headers["Range"] = "bytes=0-"
        headers.setdefault("Accept", "*/*")
        headers.setdefault("Accept-Encoding", "identity")
        return headers
    
    async def download_videos(self, video_urls: List[str], output_dir: str) -> None:
        """
        根据 URL 列表下载视频
        
        Args:
            video_urls: 视频URL列表
            output_dir: 输出目录
        """
        if not video_urls:
            logger.warning("没有视频URL可下载")
            return
        
        logger.info(f"开始下载 {len(video_urls)} 个视频到: {output_dir}")
        
        # 识别 m3u8 URL 及其基础路径，用于过滤掉属于同一流的 .ts 文件
        m3u8_base_paths = set()
        m3u8_urls = []
        for url in video_urls:
            if '.m3u8' in url.lower():
                m3u8_urls.append(url)
                # 提取 m3u8 的基础路径（例如: /hls/1011435/index.m3u8 -> /hls/1011435/）
                parsed = urlparse(url)
                path = parsed.path
                # 移除文件名，获取目录路径
                if '/' in path:
                    base_path = path[:path.rfind('/') + 1]
                    m3u8_base_paths.add(base_path)
                    logger.debug(f"检测到 m3u8 基础路径: {base_path} (来自: {url})")
        
        if m3u8_urls:
            logger.info(f"检测到 {len(m3u8_urls)} 个 m3u8 流，将优先使用 m3u8 下载完整视频")
        
        # 过滤掉属于 m3u8 流的 .ts 文件（避免重复下载）
        filtered_urls = []
        skipped_ts_count = 0
        for url in video_urls:
            if url.lower().endswith('.ts'):
                # 检查这个 .ts 文件是否属于某个已检测到的 m3u8 流
                parsed = urlparse(url)
                path = parsed.path
                is_part_of_m3u8 = False
                for base_path in m3u8_base_paths:
                    if path.startswith(base_path):
                        is_part_of_m3u8 = True
                        skipped_ts_count += 1
                        logger.debug(f"跳过 .ts 文件（属于 m3u8 流）: {url}")
                        break
                if not is_part_of_m3u8:
                    filtered_urls.append(url)
            else:
                filtered_urls.append(url)
        
        if skipped_ts_count > 0:
            logger.info(f"检测到 m3u8 流，已跳过 {skipped_ts_count} 个 .ts 文件（将使用 m3u8 下载完整视频）")
        
        headers_map = {}
        for url in filtered_urls:
            headers_map[url] = self.video_request_meta.get(url) or self._prepare_download_headers({})
        
        downloaded_files: List[str] = []
        total = len(filtered_urls)
        
        # 显示总体下载进度
        try:
            from tqdm import tqdm
            TQDM_AVAILABLE = True
        except ImportError:
            TQDM_AVAILABLE = False
            tqdm = lambda x, **kwargs: x
        
        if TQDM_AVAILABLE and total > 1:
            pbar = tqdm(
                total=total,
                desc="总体下载进度",
                unit="文件",
                ncols=100,
                position=0,
                leave=True
            )
        else:
            pbar = None
        
        try:
            for i, url in enumerate(filtered_urls):
                headers = headers_map.get(url)
                try:
                    file_path = download_video(
                        url,
                        output_dir,
                        index=i if total > 1 else None,
                        headers=headers,
                    )
                except Exception as err:
                    logger.error(f"直接下载失败 {url}: {err}")
                    file_path = None
                if file_path:
                    downloaded_files.append(file_path)
                
                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({"已完成": f"{len(downloaded_files)}/{total}"})
        finally:
            if pbar:
                pbar.close()
        
        if not downloaded_files:
            logger.error("所有下载尝试均失败")
            return
        
        logger.info(f"成功下载 {len(downloaded_files)} 个视频")
        
        # 检测并合并 .ts 文件（HLS 视频片段）
        # 注意：如果已有 m3u8 下载，通常不会有 .ts 文件需要合并
        merged_ts_files = detect_and_merge_ts_files(downloaded_files, output_dir)
        if merged_ts_files:
            logger.info(f"已合并 .ts 文件: {merged_ts_files}")
            # 从 downloaded_files 中移除已合并的 .ts 文件
            downloaded_files = [f for f in downloaded_files if not f.endswith('.ts')]
        
        # 自动合并分离的音视频流（例如 Bilibili DASH 的 .m4s）
        muxed_files = auto_mux_downloads(downloaded_files, output_dir)
        if muxed_files:
            logger.info(f"生成合并文件: {muxed_files}")
    
    async def run_async(self, url: str, output_dir: str, timeout: int = 90000) -> None:
        """
        异步执行：一键完成启动浏览器 + 收集 URL + 下载视频
        
        Args:
            url: 目标网页URL
            output_dir: 输出目录
            timeout: 超时时间（毫秒）
        """
        logger.info("=" * 60)
        logger.info("开始执行无头浏览器模式")
        logger.info(f"目标URL: {url}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("=" * 60)
        
        try:
            # 1. 收集视频URL（保持浏览器打开）
            video_urls = await self.collect_video_urls(url, timeout=timeout, keep_browser_open=True)
            
            if not video_urls:
                logger.warning("未找到任何视频URL，请检查：")
                logger.warning("1. 网站是否使用了DRM保护")
                logger.warning("2. 是否需要登录")
                logger.warning("3. 视频是否为动态加载")
                await self._cleanup_resources()
                return
            
            # 2. 下载视频（浏览器保持打开）
            await self.download_videos(video_urls, output_dir)
            
            # 3. 等待 30 秒后关闭浏览器（给用户时间查看页面或调试）
            if not self.headless:
                logger.info("下载已开始，浏览器将在 30 秒后自动关闭...")
            else:
                logger.info("下载已开始，将在 30 秒后关闭浏览器...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"执行过程中出错: {e}", exc_info=True)
        finally:
            # 关闭浏览器和 Playwright
            await self._cleanup_resources()
    
    def run(self, url: str, output_dir: str, timeout: int = 90000) -> None:
        """
        同步执行：一键完成启动浏览器 + 收集 URL + 下载视频
        
        Args:
            url: 目标网页URL
            output_dir: 输出目录
        """
        asyncio.run(self.run_async(url, output_dir, timeout=timeout))
