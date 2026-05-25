# 名著导读

基于 Dify RAG 架构的 AI 名著导读平台，覆盖四大名著，提供原著阅读与智能问答体验。

## 功能

- **四部名著覆盖**：西游记、三国演义、红楼梦、水浒传，共用知识库检索
- **双栏布局**：左栏原著阅读（章节选择 + 翻页）+ 右栏 AI 对话
- **智能问答**：向量检索 + DeepSeek V4 生成，命中原文则严谨作答，未命中则以学者风格回复
- **全文搜索**：MySQL FULLTEXT 索引，支持跨书关键词搜索章节
- **阅读进度同步**：服务端持久化，支持"继续阅读"
- **对话持久化**：localStorage 存储，按作品分组，刷新/切换不丢失
- **多轮上下文**：支持追问、指代消解
- **TTS 朗读**：支持章节正文语音朗读
- **深色模式**：跟随系统 / 手动切换
- **移动端适配**：汉堡菜单 + overlay 侧栏，触屏友好
- **管理后台**：用户列表、系统统计、健康监控

## 架构

```
[浏览器/Android App]
        │
   cpolar / Cloudflare 公网隧道
        │
[Caddy 反向代理 :80]  ← 安全头 + 请求限流
        │
[FastAPI :8080]  ← REST API + JWT 认证
        │
   Dify 知识库检索 + LLM
        │
   MySQL  ← 用户数据 + 章节内容
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + Vite，双栏布局 |
| 后端 | FastAPI + Uvicorn（V3.0.0） |
| 旧版后端 | Python http.server + JWT 认证（`scripts/serve_frontend.py`） |
| AI | Dify advanced-chat，DeepSeek V4 Flash |
| 检索 | BCE Embedding Base + BCE Reranker Base (SiliconFlow) |
| 数据库 | MySQL 8.0 |
| 部署 | Docker Compose + Caddy + cpolar/Cloudflare 隧道 |
| CI | GitHub Actions（lint + test + docker build） |

## 项目结构

```
├── server/                  # FastAPI 后端（V3.0.0）
│   ├── main.py              # 应用入口 + 生命周期
│   ├── config.py            # 环境变量配置
│   ├── routers/             # API 路由（auth/chapters/chat/reading/admin）
│   ├── models/              # Pydantic 请求/响应模型
│   ├── middleware/          # 认证/异常/日志/限流/安全中间件
│   └── services/            # 章节数据库/登录守卫
├── scripts/
│   ├── serve_frontend.py    # 旧版 HTTP 服务器（静态+API+Dify代理）
│   ├── start_fastapi.py     # FastAPI 生产启动脚本
│   ├── backup.py            # 数据库 + 数据备份脚本
│   └── import_chapters.py   # 章节文本导入 MySQL
├── backend/
│   ├── auth.py              # JWT + bcrypt 认证
│   └── db.py                # MySQL 连接管理
├── frontend/src/            # React 前端（App.jsx 主组件）
├── tests/                   # 测试（安全测试/数据完整性）
├── data/<名著>/              # 原文文本（每回一个文件）
├── docs/                    # 开发文档、需求文档
├── .github/workflows/ci.yml # CI 流水线
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose 编排
├── Caddyfile                # Caddy 反向代理配置
└── .env.example             # 环境变量模板
```

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填写数据库/Dify/JWT 配置

# 2. 构建并启动
docker-compose up -d
# 访问 http://localhost:8080
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# 配置 .env（参考 .env.example）

# 启动 FastAPI（推荐）
python scripts/start_fastapi.py
# http://127.0.0.1:8080

# 或启动旧版 HTTP 服务器
python scripts/serve_frontend.py
```

## API

| 端点 | 认证 | 说明 |
|------|------|------|
| GET /api/health | 无 | 健康检查 |
| POST /api/auth/register | 无 | 注册 |
| POST /api/auth/login | 无 | 登录 |
| GET /api/auth/me | Bearer | 当前用户 |
| GET /api/chapters?book=西游记 | 无 | 章节目录 |
| GET /api/chapters?book=西游记&chapter=1 | 无 | 章节正文 |
| GET /api/chapters/books | 无 | 所有书籍列表 |
| GET /api/chapters/search?q=大闹天宫&book=西游记 | 无 | 全文搜索 |
| POST /api/chat-messages | 无 | Dify 对话代理 |
| POST /api/reading/progress | Bearer | 保存阅读进度 |
| GET /api/reading/progress?book=西游记 | Bearer | 获取阅读进度 |
| GET /api/reading/last | Bearer | 最后阅读位置 |
| GET /api/admin/users | Bearer+管理员 | 用户列表（分页） |
| GET /api/admin/stats | Bearer+管理员 | 系统统计 |
| GET /api/admin/health | 无 | 详细健康检查 |

## 版本

V3.0.0 — FastAPI 重构 + Docker 容器化 + CI 流水线 + 全文搜索 + 深色模式 + 移动端适配 + 管理后台
