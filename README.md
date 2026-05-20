# 名著导读 (Classics Guide)

基于 Dify + RAG 的 AI 名著导读应用，以西游记为首发项目，提供智能化、交互式的经典文学阅读体验。

## 技术栈

- **AI 平台**：Dify (advanced-chat mode)
- **大语言模型**：DeepSeek V4 Flash
- **Embedding**：BCE Embedding Base
- **Reranker**：BCE Reranker Base
- **前端**：React + Vite
- **后端**：Python HTTP Server + JWT Auth
- **数据库**：MySQL 8.0

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

### 3. 初始化数据库

```bash
PYTHONPATH=. python backend/init_admin.py
```

### 4. 启动服务

```bash
PYTHONPATH=. python scripts/serve_frontend.py
```

访问 `http://localhost:8080`

## 项目结构

```
├── backend/          # 后端认证 + 数据库
├── frontend/         # React 前端
├── scripts/          # 运维脚本
├── data/             # 知识库数据
└── docs/             # 文档
```

## 配置 Dify

1. 部署 Dify 平台
2. 导入工作流配置
3. 创建知识库并上传文档
4. 配置模型提供商
5. 将 API Key 填入 .env

## 许可

MIT License
