/**
 * VideoCollector - 浏览器 Console 脚本
 * 在浏览器 Console 中运行此脚本，提取页面加载的视频 URL
 * 
 * 使用方法：
 * 1. 打开目标视频网页
 * 2. 按 F12 打开开发者工具
 * 3. 切换到 Console 标签
 * 4. 粘贴此脚本并回车
 * 5. 复制输出的 JSON
 * 6. 在 Python CLI 中使用 browser_script 模式
 */

(function () {
  /**
   * 判断 URL 是否为视频 URL
   */
  function isVideoUrl(url) {
    if (!url) return false;
    const lower = url.toLowerCase();
    return (
      lower.includes(".m3u8") ||
      lower.includes(".mp4") ||
      lower.includes(".webm") ||
      lower.includes(".flv") ||
      lower.includes(".avi") ||
      lower.includes(".mov")
    );
  }

  /**
   * 从 performance API 提取视频 URL
   */
  function extractVideoUrlsFromPerformance() {
    const resources = performance.getEntriesByType("resource");
    const videoUrls = [];

    resources.forEach((res) => {
      const url = res.name;
      if (isVideoUrl(url) && !videoUrls.includes(url)) {
        videoUrls.push(url);
      }
    });

    return videoUrls;
  }

  /**
   * 从网络请求中提取视频 URL（如果可用）
   */
  function extractVideoUrlsFromNetwork() {
    const videoUrls = [];
    
    // 尝试从 window 对象中查找视频 URL
    // 某些网站可能将视频 URL 存储在全局变量中
    if (window.__playinfo__) {
      // Bilibili 等网站可能使用此结构
      try {
        const playinfo = window.__playinfo__;
        if (playinfo.data && playinfo.data.dash) {
          // 提取 dash 流
          if (playinfo.data.dash.video) {
            playinfo.data.dash.video.forEach(v => {
              if (v.baseUrl) videoUrls.push(v.baseUrl);
            });
          }
          if (playinfo.data.dash.audio) {
            playinfo.data.dash.audio.forEach(a => {
              if (a.baseUrl) videoUrls.push(a.baseUrl);
            });
          }
        }
      } catch (e) {
        console.warn("解析 __playinfo__ 失败:", e);
      }
    }

    return videoUrls;
  }

  /**
   * 从 video 标签提取视频 URL
   */
  function extractVideoUrlsFromVideoTags() {
    const videoUrls = [];
    const videoElements = document.querySelectorAll("video");
    
    videoElements.forEach((video) => {
      if (video.src) {
        videoUrls.push(video.src);
      }
      // 检查 source 标签
      const sources = video.querySelectorAll("source");
      sources.forEach((source) => {
        if (source.src) {
          videoUrls.push(source.src);
        }
      });
    });

    return videoUrls;
  }

  // 主执行逻辑
  console.log("=".repeat(60));
  console.log("VideoCollector - 视频 URL 提取脚本");
  console.log("=".repeat(60));

  const videoUrls = new Set();

  // 方法1: 从 performance API 提取
  const perfUrls = extractVideoUrlsFromPerformance();
  perfUrls.forEach(url => videoUrls.add(url));
  console.log(`从 Performance API 找到 ${perfUrls.length} 个视频 URL`);

  // 方法2: 从网络请求提取（如果可用）
  const networkUrls = extractVideoUrlsFromNetwork();
  networkUrls.forEach(url => videoUrls.add(url));
  console.log(`从网络请求找到 ${networkUrls.length} 个视频 URL`);

  // 方法3: 从 video 标签提取
  const tagUrls = extractVideoUrlsFromVideoTags();
  tagUrls.forEach(url => videoUrls.add(url));
  console.log(`从 Video 标签找到 ${tagUrls.length} 个视频 URL`);

  const finalUrls = Array.from(videoUrls).filter(url => url && url.trim());

  console.log("\n检测到的视频 URL:");
  finalUrls.forEach((url, index) => {
    console.log(`${index + 1}. ${url}`);
  });

  if (finalUrls.length === 0) {
    console.warn("\n⚠️  未找到视频 URL！");
    console.warn("可能的原因：");
    console.warn("1. 视频使用 DRM 保护");
    console.warn("2. 视频动态加载，需要等待页面完全加载");
    console.warn("3. 视频在 iframe 中");
    console.warn("\n建议：");
    console.warn("- 等待视频开始播放后再运行脚本");
    console.warn("- 检查 Network 标签中的视频请求");
  } else {
    console.log("\n" + "=".repeat(60));
    console.log("JSON (复制以下内容):");
    console.log("=".repeat(60));
    console.log(JSON.stringify({ videoUrls: finalUrls }, null, 2));
    console.log("=".repeat(60));
  }

  // 返回结果（方便在代码中使用）
  return { videoUrls: finalUrls };
})();

