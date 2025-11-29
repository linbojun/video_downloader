"""
方案 A：Playwright 无头浏览器模式
自动打开网页 → 监听网络请求 → 匹配视频流链接（m3u8/mp4）→ 下载并合并
"""
import asyncio
import logging
from typing import List, Set, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from .utils import download_videos, is_video_url

logger = logging.getLogger(__name__)


class HeadlessBrowserDownloader:
    """Playwright 无头浏览器下载器"""
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """
        初始化 Playwright 浏览器下载器
        
        Args:
            headless: 是否使用无头模式
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
        """
        self.headless = headless
        self.browser_type = browser_type
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.video_urls: Set[str] = set()
        
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
            if is_video_url(url):
                logger.info(f"发现视频URL: {url}")
                self.video_urls.add(url)
                return
            
            # 检查 Content-Type
            content_type = headers.get('content-type', '').lower()
            if 'video' in content_type:
                logger.info(f"发现视频响应 (Content-Type: {content_type}): {url}")
                self.video_urls.add(url)
                return
                
        except Exception as e:
            logger.debug(f"处理响应时出错: {e}")
    
    async def collect_video_urls(self, url: str, timeout: int = 30000) -> List[str]:
        """
        打开网页，监听网络，收集视频 URL 列表
        
        Args:
            url: 目标网页URL
            timeout: 超时时间（毫秒）
            
        Returns:
            List[str]: 收集到的视频URL列表
        """
        self.video_urls.clear()
        
        try:
            async with async_playwright() as p:
                # 启动浏览器
                if self.browser_type == "chromium":
                    self.browser = await p.chromium.launch(headless=self.headless)
                elif self.browser_type == "firefox":
                    self.browser = await p.firefox.launch(headless=self.headless)
                elif self.browser_type == "webkit":
                    self.browser = await p.webkit.launch(headless=self.headless)
                else:
                    raise ValueError(f"不支持的浏览器类型: {self.browser_type}")
                
                logger.info(f"启动浏览器: {self.browser_type} (headless={self.headless})")
                
                # 创建上下文
                self.context = await self.browser.new_context()
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
                
                # 关闭浏览器
                await self.browser.close()
                
        except Exception as e:
            logger.error(f"收集视频URL时出错: {e}")
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
        
        video_urls_list = list(self.video_urls)
        logger.info(f"共收集到 {len(video_urls_list)} 个视频URL")
        return video_urls_list
    
    def download_videos(self, video_urls: List[str], output_dir: str) -> None:
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
        downloaded_files = download_videos(video_urls, output_dir)
        logger.info(f"成功下载 {len(downloaded_files)} 个视频")
    
    async def run_async(self, url: str, output_dir: str) -> None:
        """
        异步执行：一键完成启动浏览器 + 收集 URL + 下载视频
        
        Args:
            url: 目标网页URL
            output_dir: 输出目录
        """
        logger.info("=" * 60)
        logger.info("开始执行无头浏览器模式")
        logger.info(f"目标URL: {url}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("=" * 60)
        
        # 1. 收集视频URL
        video_urls = await self.collect_video_urls(url)
        
        if not video_urls:
            logger.warning("未找到任何视频URL，请检查：")
            logger.warning("1. 网站是否使用了DRM保护")
            logger.warning("2. 是否需要登录")
            logger.warning("3. 视频是否为动态加载")
            return
        
        # 2. 下载视频
        self.download_videos(video_urls, output_dir)
    
    def run(self, url: str, output_dir: str) -> None:
        """
        同步执行：一键完成启动浏览器 + 收集 URL + 下载视频
        
        Args:
            url: 目标网页URL
            output_dir: 输出目录
        """
        asyncio.run(self.run_async(url, output_dir))

