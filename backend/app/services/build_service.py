"""
静态博客构建引擎
支持 5 套主题模板，反同质化编译，SEO 合规拦截
"""
import os
import shutil
import zipfile
import uuid
import random
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# 主题基础目录 (容器内挂载路径)
THEMES_DIR = os.getenv("THEMES_DIR", "/app/themes")
BUILD_TMP_DIR = os.getenv("BUILD_TMP_DIR", "/tmp/blog-builds")


THEME_CONFIGS = {
    "minimal-white": {
        "description": "极简白色，阅读导向",
        "primary_color": "#1a1a1a",
        "bg_color": "#ffffff",
        "font": "Georgia, serif",
        "layout": "single-column"
    },
    "dark-tech": {
        "description": "科技暗黑，代码感强",
        "primary_color": "#00ff88",
        "bg_color": "#0d1117",
        "font": "'Fira Code', monospace",
        "layout": "terminal"
    },
    "magazine": {
        "description": "杂志风格，图文混排",
        "primary_color": "#c0392b",
        "bg_color": "#f8f9fa",
        "font": "'Playfair Display', serif",
        "layout": "multi-column"
    },
    "personal": {
        "description": "个人博客，卡片式",
        "primary_color": "#6c5ce7",
        "bg_color": "#f0f0f5",
        "font": "'Inter', sans-serif",
        "layout": "card-grid"
    },
    "enterprise": {
        "description": "企业资讯，正式SEO强化",
        "primary_color": "#0066cc",
        "bg_color": "#ffffff",
        "font": "'Noto Sans SC', sans-serif",
        "layout": "enterprise"
    }
}


def _generate_unique_class_prefix() -> str:
    """生成随机 CSS 类前缀，保证 HTML 结构差异化"""
    return f"bm{uuid.uuid4().hex[:6]}"


def _build_html_site(
    blog_name: str,
    domain: str,
    theme: str,
    content_markdown: Optional[str],
    build_id: str
) -> str:
    """
    在临时目录中构建静态站点
    返回：zip 文件路径
    """
    os.makedirs(BUILD_TMP_DIR, exist_ok=True)
    work_dir = os.path.join(BUILD_TMP_DIR, build_id)
    os.makedirs(work_dir, exist_ok=True)

    config = THEME_CONFIGS.get(theme, THEME_CONFIGS["minimal-white"])
    prefix = _generate_unique_class_prefix()

    # 随机化微变量（反同质化）
    font_size_base = random.choice([15, 16, 17])
    line_height = random.choice(["1.6", "1.7", "1.75"])
    border_radius = random.choice(["4px", "6px", "8px", "12px"])
    shadow_size = random.choice(["0 2px 8px", "0 4px 16px", "0 1px 4px"])

    content_html = _markdown_to_html(content_markdown or _default_content(blog_name))
    nav_id = f"nav-{uuid.uuid4().hex[:4]}"
    main_id = f"main-{uuid.uuid4().hex[:4]}"

    # 生成 index.html
    html = _render_html(
        blog_name=blog_name,
        domain=domain,
        theme=theme,
        config=config,
        prefix=prefix,
        font_size_base=font_size_base,
        line_height=line_height,
        border_radius=border_radius,
        shadow_size=shadow_size,
        content_html=content_html,
        nav_id=nav_id,
        main_id=main_id,
        build_id=build_id
    )

    index_path = os.path.join(work_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 生成 robots.txt（SEO 必须）
    robots_content = f"""User-agent: *
Allow: /
Sitemap: https://{domain}/sitemap.xml
"""
    with open(os.path.join(work_dir, "robots.txt"), "w") as f:
        f.write(robots_content)

    # 生成 sitemap.xml（SEO 必须）
    now = datetime.utcnow().strftime("%Y-%m-%d")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://{domain}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    with open(os.path.join(work_dir, "sitemap.xml"), "w") as f:
        f.write(sitemap)

    # 生成 404.html
    with open(os.path.join(work_dir, "404.html"), "w", encoding="utf-8") as f:
        f.write(f"<html><head><title>404 - {blog_name}</title></head><body><h1>页面未找到</h1><a href='/'>返回首页</a></body></html>")

    # 打包 zip
    zip_path = os.path.join(BUILD_TMP_DIR, f"{build_id}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work_dir)
                zf.write(file_path, arcname)

    # 清理临时目录
    shutil.rmtree(work_dir, ignore_errors=True)

    return zip_path


def _seo_validate(zip_path: str) -> Tuple[bool, list]:
    """
    SEO 合规校验
    返回 (is_valid, missing_files)
    """
    required_files = ["robots.txt", "sitemap.xml", "index.html"]
    missing = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        for req in required_files:
            if req not in names:
                missing.append(req)
    return len(missing) == 0, missing


def build_blog(
    blog_name: str,
    domain: str,
    theme: str,
    content_markdown: Optional[str] = None
) -> Tuple[str, str]:
    """
    构建博客静态包
    返回 (zip_path, build_id)
    """
    build_id = uuid.uuid4().hex[:12]
    logger.info(f"开始构建博客 [{blog_name}] 主题={theme} build_id={build_id}")

    zip_path = _build_html_site(blog_name, domain, theme, content_markdown, build_id)

    # SEO 校验
    is_valid, missing = _seo_validate(zip_path)
    if not is_valid:
        # 自动注入 robots.txt，但 sitemap 缺失则阻断
        if "sitemap.xml" in missing:
            os.remove(zip_path)
            raise ValueError(f"SEO 拦截：缺少 sitemap.xml，构建已阻断。缺失文件: {missing}")

    logger.info(f"构建完成 [{blog_name}]: {zip_path}")
    return zip_path, build_id


def cleanup_build(zip_path: str):
    """清理构建产物"""
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception as e:
        logger.warning(f"清理构建文件失败: {e}")


def _default_content(blog_name: str) -> str:
    return f"""# 欢迎来到 {blog_name}

这是您的博客首页，您可以在这里分享您的想法、故事和知识。

## 开始创作

您的内容将在这里展示。点击编辑开始您的创作之旅。

## 关于我们

专注于提供高质量的内容，服务每一位读者。
"""


def _markdown_to_html(md: str) -> str:
    """简单 Markdown 转 HTML"""
    import re
    lines = md.strip().split("\n")
    html_lines = []
    in_p = False

    for line in lines:
        line = line.rstrip()
        if line.startswith("### "):
            if in_p:
                html_lines.append("</p>")
                in_p = False
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            if in_p:
                html_lines.append("</p>")
                in_p = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            if in_p:
                html_lines.append("</p>")
                in_p = False
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line == "":
            if in_p:
                html_lines.append("</p>")
                in_p = False
        else:
            # inline bold/italic
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            if not in_p:
                html_lines.append("<p>")
                in_p = True
            html_lines.append(line)

    if in_p:
        html_lines.append("</p>")
    return "\n".join(html_lines)


def _render_html(blog_name, domain, theme, config, prefix, font_size_base,
                 line_height, border_radius, shadow_size, content_html,
                 nav_id, main_id, build_id) -> str:
    """渲染完整 HTML 页面"""
    primary = config["primary_color"]
    bg = config["bg_color"]
    font = config["font"]
    layout = config["layout"]

    # 差异化布局 CSS
    layout_css = {
        "single-column": f".{prefix}-container {{ max-width: 720px; margin: 0 auto; }}",
        "terminal": f".{prefix}-container {{ max-width: 900px; margin: 0 auto; background: #161b22; padding: 2rem; border-radius: {border_radius}; }}",
        "multi-column": f".{prefix}-container {{ max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; }}",
        "card-grid": f".{prefix}-container {{ max-width: 1100px; margin: 0 auto; }}",
        "enterprise": f".{prefix}-container {{ max-width: 1000px; margin: 0 auto; }}",
    }.get(layout, f".{prefix}-container {{ max-width: 800px; margin: 0 auto; }}")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="index, follow">
  <meta name="description" content="{blog_name} - 专业内容平台">
  <meta property="og:title" content="{blog_name}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://{domain}/">
  <link rel="canonical" href="https://{domain}/">
  <link rel="sitemap" type="application/xml" href="/sitemap.xml">
  <title>{blog_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --{prefix}-primary: {primary};
      --{prefix}-bg: {bg};
      --{prefix}-font: {font};
      --{prefix}-radius: {border_radius};
      --{prefix}-shadow: {shadow_size} rgba(0,0,0,0.1);
    }}
    body {{
      font-family: var(--{prefix}-font);
      background-color: var(--{prefix}-bg);
      color: {'#e6edf3' if theme == 'dark-tech' else '#333'};
      font-size: {font_size_base}px;
      line-height: {line_height};
      padding: 0;
    }}
    #{nav_id} {{
      background: var(--{prefix}-primary);
      color: #fff;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: var(--{prefix}-shadow);
    }}
    #{nav_id} .{prefix}-logo {{
      font-size: 1.4rem;
      font-weight: 700;
      text-decoration: none;
      color: #fff;
    }}
    #{main_id} {{
      padding: 2.5rem 1.5rem;
    }}
    {layout_css}
    .{prefix}-content h1 {{ font-size: 2rem; margin-bottom: 1.2rem; color: var(--{prefix}-primary); }}
    .{prefix}-content h2 {{ font-size: 1.5rem; margin: 2rem 0 0.8rem; border-bottom: 2px solid var(--{prefix}-primary); padding-bottom: 0.4rem; }}
    .{prefix}-content h3 {{ font-size: 1.2rem; margin: 1.5rem 0 0.6rem; }}
    .{prefix}-content p {{ margin-bottom: 1.2rem; }}
    .{prefix}-footer {{
      text-align: center;
      padding: 2rem;
      color: #999;
      font-size: 0.85rem;
      border-top: 1px solid #eee;
      margin-top: 3rem;
    }}
    @media (max-width: 768px) {{
      .{prefix}-container {{ padding: 0 1rem; }}
      #{nav_id} {{ flex-direction: column; gap: 0.5rem; }}
    }}
  </style>
</head>
<body>
  <nav id="{nav_id}">
    <a href="/" class="{prefix}-logo">{blog_name}</a>
    <span class="{prefix}-nav-links">
      <a href="/" style="color:#fff;text-decoration:none;margin-left:1.5rem;">首页</a>
      <a href="/sitemap.xml" style="color:#fff;text-decoration:none;margin-left:1.5rem;">站点地图</a>
    </span>
  </nav>
  <main id="{main_id}">
    <div class="{prefix}-container">
      <article class="{prefix}-content">
        {content_html}
      </article>
    </div>
  </main>
  <footer class="{prefix}-footer">
    <p>&copy; {datetime.now().year} {blog_name} · 由博客矩阵平台驱动</p>
  </footer>
  <!-- build:{build_id} theme:{theme} -->
</body>
</html>"""
