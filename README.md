# 名著导读 (Classics Guide)

基于 Dify + RAG 的 AI 名著导读应用，覆盖四大名著，提供原著阅读与智能问答。

## 功能

- 四部名著：西游记、三国演义、红楼梦、水浒传
- 双栏布局：左栏原文阅读 + 右栏 AI 对话
- 智能问答：知识库检索 + DeepSeek V4 生成
- 多轮对话：支持追问与指代消解
- 对话持久化、阅读进度记忆

## 技术栈

- **AI 平台**：Dify (advanced-chat mode)
- **LLM**：DeepSeek V4 Flash
- **Embedding**：BCE Embedding Base
- **Reranker**：BCE Reranker Base
- **前端**：React + Vite
- **后端**：Python HTTP Server + JWT Auth
- **数据库**：MySQL 8.0

## 快速开始

```bash
cp .env.example .env
# 编辑 .env 填入你的配置

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

PYTHONPATH=. python backend/init_admin.py
PYTHONPATH=. python scripts/serve_frontend.py
```

访问 `http://localhost:8080`

## 配置 Dify

1. 部署 Dify 平台
2. 导入工作流配置
3. 创建知识库并上传文档
4. 配置模型提供商
5. 将 API Key 填入 .env

## 许可

MIT License
