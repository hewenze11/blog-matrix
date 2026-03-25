"""
Hugo 静态博客构建引擎（v2）
使用 Hugo + 开源主题替代手写 HTML，生成真正美观的博客站点
"""
import os
import shutil
import zipfile
import uuid
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

BUILD_TMP_DIR = os.getenv("BUILD_TMP_DIR", "/tmp/blog-builds")
THEMES_CACHE_DIR = os.getenv("HUGO_THEMES_DIR", "/app/hugo-themes")
HUGO_BIN = "/usr/local/bin/hugo"

# 主题配置映射
THEME_MAP = {
    "minimal-white": {
        "hugo_theme": "PaperMod",
        "git_url": "https://github.com/adityatelange/hugo-PaperMod.git",
        "config_extra": """
[params]
  ShowReadingTime = true
  ShowShareButtons = false
  ShowPostNavLinks = true
  ShowBreadCrumbs = true
  ShowCodeCopyButtons = true
  ShowFullTextinRSS = true
  homeInfoParams.Title = ""
  homeInfoParams.Content = ""
"""
    },
    "dark-tech": {
        "hugo_theme": "terminal",
        "git_url": "https://github.com/panr/hugo-theme-terminal.git",
        "config_extra": """
[params]
  showMenuItems = 2
  fullWidthTheme = false
  centerTheme = false
  autoCover = true
  showLastUpdated = false
  [params.twitter]
    creator = ""
    site = ""
"""
    },
    "magazine": {
        "hugo_theme": "newspaper",
        "git_url": "https://github.com/ThanksForAllTheFish/newspaper.git",
        "config_extra": """
[params]
  description = "Latest news and articles"
"""
    },
    "personal": {
        "hugo_theme": "hello-friend-ng",
        "git_url": "https://github.com/rhazdon/hugo-theme-hello-friend-ng.git",
        "config_extra": """
[params]
  dateform = "Jan 2, 2006"
  dateformShort = "Jan 2"
  dateformNum = "2006-01-02"
  dateformNumTime = "2006-01-02 15:04"
  enableGlobalLanguageMenu = false
  fingerprintAlgorithm = "sha256"
  subtitle = ""
  [params.logo]
    logoMark = ""
    logoText = ""
    logoHomeLink = "/"
"""
    },
    "enterprise": {
        "hugo_theme": "small-business",
        "git_url": "https://github.com/themefisher/small-business.git",
        "config_extra": """
[params]
  description = "Professional business solutions"
"""
    },
}


def _ensure_hugo_installed() -> bool:
    """确认 Hugo 已安装"""
    result = subprocess.run([HUGO_BIN, "version"], capture_output=True, text=True)
    return result.returncode == 0


def _ensure_theme_cached(theme_key: str) -> Optional[str]:
    """
    确保主题已缓存到 THEMES_CACHE_DIR，返回缓存路径
    """
    theme_config = THEME_MAP.get(theme_key)
    if not theme_config:
        logger.error(f"未知主题: {theme_key}")
        return None

    theme_dir = os.path.join(THEMES_CACHE_DIR, theme_config["hugo_theme"])
    os.makedirs(THEMES_CACHE_DIR, exist_ok=True)

    if os.path.isdir(theme_dir) and os.listdir(theme_dir):
        return theme_dir

    # clone 主题
    logger.info(f"正在下载主题 {theme_config['hugo_theme']}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", theme_config["git_url"], theme_dir],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        logger.error(f"主题 {theme_config['hugo_theme']} 下载失败: {result.stderr}")
        # 清理失败的目录
        shutil.rmtree(theme_dir, ignore_errors=True)
        return None

    return theme_dir


def _generate_config(blog_name: str, domain: str, theme_key: str, build_id: str) -> str:
    """生成 Hugo config.toml"""
    theme_config = THEME_MAP.get(theme_key, THEME_MAP["minimal-white"])
    hugo_theme = theme_config["hugo_theme"]
    config_extra = theme_config.get("config_extra", "")

    base_url = f"https://{domain}/"

    return f"""baseURL = "{base_url}"
languageCode = "zh-cn"
defaultContentLanguage = "zh-cn"
title = "{blog_name}"
theme = "{hugo_theme}"
paginate = 5
enableRobotsTXT = true
enableEmoji = true

[outputs]
  home = ["HTML", "RSS", "JSON"]

[sitemap]
  changefreq = "weekly"
  priority = 0.5

[params]
  env = "production"
  title = "{blog_name}"
  description = "{blog_name} - 专业内容平台"
  keywords = []
  author = "{blog_name}"
  images = []
  DateFormat = "January 2, 2006"
  defaultTheme = "auto"
  disableThemeToggle = false
  ShowReadingTime = true
  ShowShareButtons = false
  ShowPostNavLinks = true
  ShowBreadCrumbs = true
  ShowCodeCopyButtons = true

[menu]
  [[menu.main]]
    identifier = "home"
    name = "首页"
    url = "/"
    weight = 10
  [[menu.main]]
    identifier = "posts"
    name = "文章"
    url = "/posts/"
    weight = 20

{config_extra}
"""


def _generate_index_md(blog_name: str) -> str:
    """生成首页 Markdown"""
    return f"""---
title: "欢迎来到 {blog_name}"
date: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}
draft: false
---

欢迎访问 **{blog_name}**，这里汇聚了最新、最实用的内容资讯。
"""


def _generate_post_md(blog_name: str, content_markdown: Optional[str], build_id: str) -> str:
    """生成文章页 Markdown（带 Hugo frontmatter）"""
    title = f"{blog_name} - 精选内容"
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    content = content_markdown or f"""
## 关于我们

{blog_name} 致力于为您提供高质量的内容和深度解析。

## 最新动态

我们持续更新行业最新资讯，欢迎收藏并关注。

## 联系我们

如有任何问题，欢迎通过官网联系我们。
"""

    return f"""---
title: "{title}"
date: {now}
draft: false
description: "{blog_name} 最新精选内容"
tags: []
categories: []
author: "{blog_name}"
showToc: true
TocOpen: false
hidemeta: false
comments: false
searchHidden: false
ShowReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
---

{content}
"""


def build_blog(
    blog_name: str,
    domain: str,
    theme: str,
    content_markdown: Optional[str] = None,
    blog_id: str = ""
) -> Tuple[str, str]:
    """
    用 Hugo 构建博客静态包
    返回 (zip_path, build_id)
    """
    build_id = uuid.uuid4().hex[:12]
    logger.info(f"Hugo 构建开始 [{blog_name}] 主题={theme} build_id={build_id}")

    # 确认 Hugo 可用
    if not _ensure_hugo_installed():
        raise RuntimeError(f"Hugo 未安装或不可用: {HUGO_BIN}")

    # 确保主题缓存
    theme_cache_dir = _ensure_theme_cached(theme)
    if not theme_cache_dir:
        # 降级到 PaperMod（最可靠的主题）
        logger.warning(f"主题 {theme} 加载失败，降级到 PaperMod")
        theme = "minimal-white"
        theme_cache_dir = _ensure_theme_cached(theme)
        if not theme_cache_dir:
            raise RuntimeError("主题加载失败，请检查网络连接")

    os.makedirs(BUILD_TMP_DIR, exist_ok=True)
    site_dir = os.path.join(BUILD_TMP_DIR, f"site-{build_id}")

    try:
        # 1. 创建 Hugo 站点骨架
        result = subprocess.run(
            [HUGO_BIN, "new", "site", site_dir, "--force"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"hugo new site 失败: {result.stderr}")

        # 2. 复制主题到站点
        theme_name = THEME_MAP[theme]["hugo_theme"]
        site_theme_dir = os.path.join(site_dir, "themes", theme_name)
        shutil.copytree(theme_cache_dir, site_theme_dir, dirs_exist_ok=False)

        # 3. 写入 config.toml
        config_content = _generate_config(blog_name, domain, theme, build_id)
        with open(os.path.join(site_dir, "config.toml"), "w", encoding="utf-8") as f:
            f.write(config_content)

        # 4. 创建内容文件
        posts_dir = os.path.join(site_dir, "content", "posts")
        os.makedirs(posts_dir, exist_ok=True)

        # 首页
        with open(os.path.join(site_dir, "content", "_index.md"), "w", encoding="utf-8") as f:
            f.write(_generate_index_md(blog_name))

        # 文章
        post_filename = os.path.join(posts_dir, f"{build_id[:8]}.md")
        with open(post_filename, "w", encoding="utf-8") as f:
            f.write(_generate_post_md(blog_name, content_markdown, build_id))

        # 5. 执行 Hugo 构建
        result = subprocess.run(
            [HUGO_BIN, "--minify", "--destination", "public"],
            cwd=site_dir,
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "HUGO_ENV": "production"}
        )
        if result.returncode != 0:
            logger.warning(f"Hugo 构建警告（可能有主题兼容问题）: {result.stderr[:500]}")
            # 尝试不带 --minify 再构建一次
            result2 = subprocess.run(
                [HUGO_BIN, "--destination", "public"],
                cwd=site_dir,
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "HUGO_ENV": "production"}
            )
            if result2.returncode != 0:
                raise RuntimeError(f"Hugo 构建失败: {result2.stderr[:300]}")

        public_dir = os.path.join(site_dir, "public")
        if not os.path.exists(public_dir) or not os.listdir(public_dir):
            raise RuntimeError("Hugo 构建未生成任何文件")

        # 6. SEO 校验（Hugo 自动生成 robots.txt 和 sitemap.xml，但验证一下）
        if not os.path.exists(os.path.join(public_dir, "sitemap.xml")):
            logger.warning("Hugo 未生成 sitemap.xml，手动创建")
            now_str = datetime.utcnow().strftime("%Y-%m-%d")
            with open(os.path.join(public_dir, "sitemap.xml"), "w") as f:
                f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://{domain}/</loc><lastmod>{now_str}</lastmod><priority>1.0</priority></url>
</urlset>""")

        if not os.path.exists(os.path.join(public_dir, "robots.txt")):
            with open(os.path.join(public_dir, "robots.txt"), "w") as f:
                f.write(f"User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n")

        # 7. 注入访问追踪 JS（如果 blog_id 存在，插入到 index.html）
        if blog_id:
            index_html = os.path.join(public_dir, "index.html")
            if os.path.exists(index_html):
                tracking_js = f"""
<script>
(function(){{
  var API='https://boke.apimart.ai/api/v1/stats/collect';
  var BID='{blog_id}';
  if(!BID)return;
  var dev=/Mobi|Android/i.test(navigator.userAgent)?'mobile':'desktop';
  function report(evt){{fetch(API,{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{blog_id:BID,event:evt,device:dev,referrer:document.referrer||''}})
  }}).catch(function(){{}});}}
  report('pageview');
  document.addEventListener('click',function(e){{
    var a=e.target&&e.target.closest?e.target.closest('a'):null;
    if(!a)return;
    report((a.href||'').indexOf('apimart')>=0?'click_apimart':'click_other');
  }});
}})();
</script>
</body>"""
                with open(index_html, "r", encoding="utf-8") as f:
                    html_content = f.read()
                html_content = html_content.replace("</body>", tracking_js)
                with open(index_html, "w", encoding="utf-8") as f:
                    f.write(html_content)

        # 8. 打包 zip
        zip_path = os.path.join(BUILD_TMP_DIR, f"{build_id}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(public_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, public_dir)
                    zf.write(file_path, arcname)

        logger.info(f"Hugo 构建完成 [{blog_name}]: {zip_path}")
        return zip_path, build_id

    finally:
        # 清理站点临时目录（保留 zip）
        shutil.rmtree(site_dir, ignore_errors=True)


def cleanup_build(zip_path: str):
    """清理构建产物"""
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception as e:
        logger.warning(f"清理构建文件失败: {e}")
