FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    git \
    nodejs \
    npm \
    && npm install -g wrangler@3 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Hugo Extended
RUN curl -L https://github.com/gohugoio/hugo/releases/download/v0.128.0/hugo_extended_0.128.0_linux-amd64.tar.gz \
    -o /tmp/hugo.tar.gz && \
    tar -xzf /tmp/hugo.tar.gz -C /usr/local/bin hugo && \
    rm /tmp/hugo.tar.gz && \
    hugo version

# 预下载 Hugo 主题（缓存到镜像层，避免每次构建时下载）
RUN mkdir -p /app/hugo-themes && \
    git clone --depth=1 https://github.com/adityatelange/hugo-PaperMod.git /app/hugo-themes/PaperMod && \
    git clone --depth=1 https://github.com/panr/hugo-theme-terminal.git /app/hugo-themes/terminal && \
    git clone --depth=1 https://github.com/rhazdon/hugo-theme-hello-friend-ng.git /app/hugo-themes/hello-friend-ng && \
    git clone --depth=1 https://github.com/themefisher/small-business.git /app/hugo-themes/small-business || true && \
    git clone --depth=1 https://github.com/ThanksForAllTheFish/newspaper.git /app/hugo-themes/newspaper || true

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY app/ ./app/

# 创建构建临时目录和主题目录
RUN mkdir -p /tmp/blog-builds /app/themes

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
