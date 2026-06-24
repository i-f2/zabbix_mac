# =============================================================================
# Zabbix Monitor as Code (MaC) - 生产环境 Dockerfile
# =============================================================================
# 目标平台: Intel Linux (linux/amd64)
# 在 Apple Silicon Mac 上构建 Intel Linux 镜像:
#   docker build --platform linux/amd64 -t zabbix-mac:YYYYMMDDvN ./
# 在 Intel Linux 上构建:
#   docker build -t zabbix-mac:YYYYMMDDvN .
# =============================================================================

FROM docker.m.daocloud.io/library/python:3.11-slim-bookworm

WORKDIR /app

# 安装系统依赖（psycopg2 编译需要 libpq-dev 和 gcc）
RUN sed -i.bak 's#http://deb.debian.org#https://mirrors.cloud.tencent.com#g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（利用 Docker 缓存层）
COPY requirements-linux-x86.txt .
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements-linux-x86.txt

# 复制应用代码
COPY app.py .
COPY zabbix_mac.py .
COPY config_loader.py .
COPY config.yaml.example .
COPY templates/ ./templates/
COPY static/ ./static/

# 创建非 root 用户运行应用
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# 启动 Flask 应用
CMD ["python", "app.py"]
