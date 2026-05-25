# CHANGELOG

## V3.0.0 (2026-05-25)

### 后端
- http.server → FastAPI + Uvicorn 模块化架构
- JWT 依赖注入 + Pydantic 数据校验
- 双通道日志系统（控制台 + 文件滚动，保留 30 天）
- API 限流（slowapi，6 端点分级）+ 登录失败锁定
- 全局异常捕获（404/405/422/500/503）
- 安全响应头中间件（X-Frame/Content-Type/XSS/Referrer）
- 管理员 API（用户列表/系统统计/健康检查）

### 数据
- 445 章原文从 txt 迁移到 MySQL（FULLTEXT 索引）
- 全文搜索 API（/api/chapters/search）
- 阅读历史服务端同步（reading_history 表 + /api/reading/*）
- 书籍列表 API（/api/chapters/books）

### 运维
- Docker + docker-compose + Caddy 反向代理
- 自动化备份脚本 + Windows 计划任务
- GitHub Actions CI 流水线（lint + test + build + docker）

### 前端
- 章节全文搜索框
- 阅读进度服务端同步
- 深色模式（跟随系统/手动切换）
- 移动端响应式适配（汉堡菜单/overlay 侧栏）
- 管理后台页面（用户列表/系统统计/健康监控）

### 安全
- 安全响应头（X-Frame-Options/Content-Type-Options/XSS-Protection）
- Caddy 反向代理层安全头
- API 限流 + 登录暴力破解防护
- 隐私数据扫描与脱敏

---

## 更早版本

### V2.2.0 (2026-05-23)

- TTS 原文朗读（Web Speech API、播放/暂停/停止、段落高亮、进度条拖动）

### V2.1.0 (2026-05-23)

- 四部名著知识库全部上线
- 双栏布局（左栏原著阅读 + 右栏 AI 对话）
- 章节 API（GET /api/chapters）
- API Key 安全改造（前端不再硬编码）
- 对话持久化 + 多轮对话上下文
- 阅读进度记忆

### V2.0.0 (2026-05-19)

- 自定义前端（React + Vite）
- 作品切换框架（四大名著）
- 推荐问题引导 + 用户反馈机制

### V1.1 (2026-05-19)

- Dify 迁移至 your-dify-server:port
- 文档补充 + Prompt 优化
- 参数调优（score=0.35, keyword_weight=0.5）

### V1.0 (2026-05-18)

- 首发《西游记》AI 导读
- Dify advanced-chat 工作流
- 108 文档知识库 + 向量化
