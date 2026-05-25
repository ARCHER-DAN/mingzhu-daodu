# ============================================================================
# 名著导读 — 容器化部署
# 名著导读 API V3.0.0 + 前端 SPA
# ============================================================================

FROM python:3.11-slim

LABEL maintainer="运维 <ops@example.com>"
LABEL description="名著导读 AI 名著导读平台 — FastAPI + React SPA"
LABEL version="3.0.0"

WORKDIR /app

# ---------------------------------------------------------------------------
# 系统依赖（curl 用于健康检查）
# ---------------------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python 依赖
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# 应用代码
# ---------------------------------------------------------------------------
COPY server/ ./server/
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY frontend/dist/ ./frontend/dist/

# ============================================================================
# 注意：.env 不复制到镜像中（含 JWT_SECRET / DB 密码 / API Key）
# 运行时通过 docker-compose 卷挂载注入（:ro 只读）
# ============================================================================

# ---------------------------------------------------------------------------
# 运行时配置
# ---------------------------------------------------------------------------
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# 以非 root 用户运行（安全加固）
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["python", "scripts/start_fastapi.py"]
