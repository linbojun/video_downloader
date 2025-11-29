#!/usr/bin/env python3
"""
VideoCollector - 通用视频下载工具
支持 Bilibili、中国抖音、常见视频网站

CLI 入口文件
"""
import argparse
import logging
import sys
from pathlib import Path
from downloader.headless_browser_mode import HeadlessBrowserDownloader
from downloader.browser_script_mode import run as run_browser_script_mode

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/video_collector.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='VideoCollector - 通用视频下载工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 方案 A: 无头浏览器模式
  python main.py --mode headless --url https://www.bilibili.com/video/BVxxxxx --output-dir ./downloads

  # 方案 B: 浏览器脚本模式
  python main.py --mode browser_script --output-dir ./downloads
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['headless', 'browser_script', 'crawler'],
        required=True,
        help='下载模式: headless (无头浏览器), browser_script (浏览器脚本), crawler (预留)'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='目标网页URL (仅 headless 模式需要)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./downloads',
        help='输出目录 (默认: ./downloads)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='使用无头模式 (默认: True)'
    )
    
    parser.add_argument(
        '--no-headless',
        dest='headless',
        action='store_false',
        help='不使用无头模式（显示浏览器窗口）'
    )
    
    parser.add_argument(
        '--browser-type',
        type=str,
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='浏览器类型 (默认: chromium)'
    )
    
    parser.add_argument(
        '--browser-channel',
        type=str,
        help='Playwright 浏览器通道，仅对 chromium 生效 (例如: chrome, chrome-beta, msedge)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30000,
        help='超时时间（毫秒）(默认: 30000)'
    )
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建日志目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    try:
        if args.mode == 'headless':
            # 方案 A: 无头浏览器模式
            if not args.url:
                logger.error("headless 模式需要提供 --url 参数")
                parser.print_help()
                sys.exit(1)
            
            logger.info("使用无头浏览器模式")
            downloader = HeadlessBrowserDownloader(
                headless=args.headless,
                browser_type=args.browser_type,
                browser_channel=args.browser_channel
            )
            downloader.run(args.url, str(output_dir))
            
        elif args.mode == 'browser_script':
            # 方案 B: 浏览器脚本模式
            logger.info("使用浏览器脚本模式")
            run_browser_script_mode(str(output_dir))
            
        elif args.mode == 'crawler':
            # TODO: 预留功能
            logger.warning("crawler 模式尚未实现")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

