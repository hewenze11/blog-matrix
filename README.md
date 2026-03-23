# 博客矩阵平台 / Blog Matrix Platform

> 企业级静态博客矩阵管理平台，基于 Cloudflare Pages 多账号调度

[![CI/CD](https://github.com/hewenze11/blog-matrix/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/hewenze11/blog-matrix/actions)

## ✨ 核心功能

- **多 CF 账号池**：录入多套 Cloudflare 账号，自动负载均衡分配
- **博客一键发布**：5 套差异化主题（反同质化），自动构建 & 部署
- **任务队列**：串行编译（`asyncio.Semaphore(1)`），防止并发 OOM
- **CNAME 傻瓜引导**：弹窗引导配置 DNS，支持阿里云/腾讯云/GoDaddy 等
- **SEO 拦截**：自动注入 robots.txt，sitemap.xml 缺失则阻断流水线
- **探活监控**：3 分钟/次异步检测，连续 3 次失败触发飞书告警
- **JWT 鉴权**：完整登录系统，Token 24h 有效期

## 🚀 一键部署

```bash
curl -fsSL https://raw.githubusercontent.com/hewenze11/blog-matrix/main/deploy.sh | bash
```

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy + PostgreSQL |
| 前端 | Next.js 14 + Tailwind CSS |
| 队列 | asyncio.Semaphore（串行防OOM） |
| 容器 | Docker + Docker Compose |
| CI/CD | GitHub Actions → GHCR |
| 反向代理 | Nginx |

## 📡 API 文档

部署后访问 `http://<server>/docs` 查看 Swagger 文档

## 默认账号

- 用户名：`admin`
- 密码：`BlogMatrix2024!`

> ⚠️ 请首次登录后立即修改密码
