#!/usr/bin/env python3
"""
Dify 平台自动化部署脚本 (纯 API 版本)
=====================================
功能：
  S1-T05: 创建知识库「名著导读-西游记」并上传108个文档，等待向量化完成
  S1-T06: 更新工作流中的知识库 ID，发布应用

基于 Dify Console API (自托管版)，无需浏览器。

用法：
  python dify_deploy.py                              # 默认执行全部
  python dify_deploy.py --skip-knowledge              # 跳过知识库创建
  python dify_deploy.py --skip-workflow               # 跳过工作流更新
  python dify_deploy.py --dataset-id <id>             # 使用已有知识库 ID
  python dify_deploy.py --app-id <id>                 # 使用已有应用 ID
  python dify_deploy.py --dry-run                     # 干跑模式，仅验证连接
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests

# ==================== 全局配置 ====================

DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://your-dify-server:port")
DIFY_EMAIL = os.environ.get("DIFY_EMAIL", os.environ.get('DIFY_EMAIL', ''))
DIFY_PASSWORD = os.environ.get("DIFY_PASSWORD", os.environ.get('DIFY_PASSWORD', ''))
DATA_DIR = Path(r"D:\kaifa\Introduction_Classics\Introduction_Classics_main\data\西游记")
WORKFLOW_FILE = Path(r"D:\kaifa\Introduction_Classics\03_工作流\名著导读.yml")
SCRIPT_DIR = Path(__file__).parent.resolve()

# 知识库配置
KB_NAME = "名著导读-西游记"
KB_DESCRIPTION = (
    "《西游记》原著全文100回、人物资料、章节概要及文学评论，"
    "用于名著导读智能问答。"
)
EMBEDDING_MODEL_DISPLAY = "bce-embedding-base_v1"
EMBEDDING_MODEL_FULL = "netease-youdao/bce-embedding-base_v1"
EMBEDDING_PROVIDER_FULL = "langgenius/siliconflow/siliconflow"
RERANKER_MODEL_DISPLAY = "bce-reranker-base_v1"
RERANKER_MODEL_FULL = "netease-youdao/bce-reranker-base_v1"
RERANKER_PROVIDER = "langgenius/siliconflow/siliconflow"
TOP_K = 4

# 默认应用 ID (名著导读)
DEFAULT_APP_ID = "d7789d4d-4b2d-4b45-b01a-26cdd5e2313f"

# 超时与重试
VECTORIZE_POLL_SEC = 5
VECTORIZE_MAX_WAIT_SEC = 600
BATCH_SIZE = 10
BATCH_UPLOAD_GAP_SEC = 3
RETRY_COUNT = 3
REQUEST_TIMEOUT = 60  # 文件上传超时


# ==================== 辅助工具 ====================

def log(level: str, msg: str):
    """带时间戳的日志输出"""
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "info": "  [INFO]", "ok": "   [OK]", "warn": " [WARN]",
        "err": "[ERROR]", "step": " [STEP]",
    }
    print(f"[{ts}]{prefix.get(level, ' [----]')} {msg}")


def collect_files(base_dir: Path) -> List[Path]:
    """收集 data/西游记/ 下所有需要上传的文件。"""
    files: List[Path] = []

    # 01_原著原文
    yuanzhu = base_dir / "01_原著原文"
    if yuanzhu.is_dir():
        txts = sorted(yuanzhu.glob("*.txt"))
        files.extend(txts)
        log("info", f"收集原著原文: {len(txts)} 个")
    else:
        log("warn", f"目录不存在: {yuanzhu}")

    # 04_文学评论
    pinglun = base_dir / "04_文学评论"
    if pinglun.is_dir():
        mds = sorted(pinglun.glob("*.md"))
        files.extend(mds)
        log("info", f"收集文学评论: {len(mds)} 个")
    else:
        log("warn", f"目录不存在: {pinglun}")

    # 根目录下的 md
    for f in sorted(base_dir.glob("*.md")):
        if f not in files:
            files.append(f)
    log("info", f"收集根目录 md: {len([f for f in files if f.parent == base_dir])} 个")

    log("info", f"总计待上传文件: {len(files)} 个")
    for f in files:
        log("info", f"  {f.relative_to(base_dir)}")
    return files


# ==================== Dify Console API 客户端 ====================

class DifyAPI:
    """Dify Console API 封装"""

    def __init__(self, base_url: str = DIFY_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.csrf_token: Optional[str] = None
        self._logged_in = False

    # ---------- 认证 ----------

    def login(self, email: str = DIFY_EMAIL, password: str = DIFY_PASSWORD) -> bool:
        """登录并获取会话 CSRF token"""
        encoded_pw = base64.b64encode(password.encode()).decode()

        resp = self.session.post(
            f"{self.base_url}/console/api/login",
            json={"email": email, "password": encoded_pw, "remember_me": True},
            timeout=REQUEST_TIMEOUT
        )

        if not resp.ok:
            log("err", f"登录失败: {resp.status_code} {resp.text}")
            return False

        for cookie in self.session.cookies:
            if cookie.name == 'csrf_token':
                self.csrf_token = cookie.value
                break

        if not self.csrf_token:
            log("err", "未获取到 CSRF token")
            return False

        self._logged_in = True
        log("ok", f"登录成功")
        return True

    @property
    def _headers(self) -> dict:
        """获取带 CSRF token 的请求头"""
        return {'X-CSRF-Token': self.csrf_token or ''}

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """统一请求方法，自动添加 CSRF token"""
        url = f"{self.base_url}{path}" if path.startswith('/') else f"{self.base_url}/{path}"
        kwargs.setdefault('headers', {}).update(self._headers)
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        return self.session.request(method, url, **kwargs)

    # ---------- 知识库操作 ----------

    def create_dataset(self, name: str, description: str = "",
                       indexing_technique: str = "high_quality") -> Optional[str]:
        """创建空知识库，返回 dataset_id；若重名则复用已有"""
        # 先查是否存在同名
        existing = self.get_datasets()
        for ds in existing:
            if ds.get('name') == name:
                ds_id = ds['id']
                log("ok", f"知识库已存在，复用: {name} (ID: {ds_id})")
                return ds_id

        resp = self._request('POST', '/console/api/datasets', json={
            "name": name,
            "description": description,
            "indexing_technique": indexing_technique,
            "permission": "only_me",
            "provider": "vendor"
        })

        if resp.status_code in (200, 201):
            ds_id = resp.json().get('id')
            log("ok", f"知识库创建成功: {name} (ID: {ds_id})")
            return ds_id
        else:
            log("err", f"创建知识库失败: {resp.status_code} {resp.text[:300]}")
            return None

    def get_datasets(self, page: int = 1, limit: int = 50) -> list:
        """获取知识库列表"""
        resp = self._request('GET', '/console/api/datasets',
                            params={"page": page, "limit": limit})
        return resp.json().get('data', []) if resp.ok else []

    def get_dataset(self, dataset_id: str) -> Optional[dict]:
        """获取单个知识库详情"""
        resp = self._request('GET', f'/console/api/datasets/{dataset_id}')
        return resp.json() if resp.ok else None

    def update_dataset(self, dataset_id: str, **kwargs) -> bool:
        """更新知识库设置"""
        resp = self._request('PATCH', f'/console/api/datasets/{dataset_id}',
                            json=kwargs)
        ok = resp.ok
        if ok:
            log("ok", "知识库设置更新成功")
        else:
            log("err", f"知识库设置更新失败: {resp.status_code} {resp.text[:300]}")
        return ok

    def configure_kb_settings(self, dataset_id: str) -> bool:
        """配置知识库的 Embedding / Reranker / Top K"""
        log("step", "配置知识库模型参数...")

        return self.update_dataset(dataset_id,
            embedding_model=EMBEDDING_MODEL_FULL,
            embedding_model_provider=EMBEDDING_PROVIDER_FULL,
            retrieval_model={
                "search_method": "semantic_search",
                "reranking_enable": True,
                "reranking_model": {
                    "reranking_provider_name": RERANKER_PROVIDER,
                    "reranking_model_name": RERANKER_MODEL_FULL
                },
                "top_k": TOP_K,
                "score_threshold_enabled": False
            }
        )

    # ---------- 文件上传 ----------

    MIME_MAP = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.pdf': 'application/pdf',
        '.csv': 'text/csv',
        '.html': 'text/html',
    }

    def upload_file(self, file_path: Path) -> Optional[str]:
        """上传单个文件到 Dify，返回 file_id"""
        if not file_path.exists():
            log("err", f"文件不存在: {file_path}")
            return None

        mime_type = self.MIME_MAP.get(file_path.suffix.lower(), 'application/octet-stream')
        file_name = file_path.name

        with open(file_path, 'rb') as fh:
            resp = self._request('POST', '/console/api/files/upload',
                                files={'file': (file_name, fh, mime_type)})

        if resp.status_code in (200, 201):
            file_id = resp.json().get('id')
            log("ok", f"上传: {file_name} (ID: {file_id})")
            return file_id
        else:
            log("err", f"上传失败 {file_name}: {resp.status_code} {resp.text[:200]}")
            return None

    def upload_files_batch(self, file_paths: List[Path]) -> List[str]:
        """批量上传文件，返回 file_id 列表"""
        file_ids = []
        total = len(file_paths)
        for i, fp in enumerate(file_paths, 1):
            fid = self.upload_file(fp)
            if fid:
                file_ids.append(fid)
                log("info", f"[{i}/{total}] OK: {fp.name}")
            time.sleep(0.3)
        return file_ids

    # ---------- 文档创建 ----------

    def create_documents(self, dataset_id: str, file_ids: List[str],
                         indexing_technique: str = "high_quality") -> Optional[dict]:
        """通过 file_ids 批量创建文档"""
        resp = self._request('POST',
            f'/console/api/datasets/{dataset_id}/documents',
            json={
                "data_source": {
                    "type": "upload_file",
                    "info_list": {
                        "data_source_type": "upload_file",
                        "file_info_list": {
                            "file_ids": file_ids
                        }
                    }
                },
                "indexing_technique": indexing_technique,
                "process_rule": {"mode": "automatic"},
                "doc_form": "text_model"
            })

        if resp.status_code in (200, 201):
            data = resp.json()
            batch = data.get('batch', '?')
            log("ok", f"文档创建成功 (Batch: {batch}, {len(file_ids)} 个文件)")
            return data
        else:
            log("err", f"文档创建失败: {resp.status_code} {resp.text[:500]}")
            return None

    def get_documents(self, dataset_id: str, page: int = 1, limit: int = 200) -> dict:
        """获取知识库文档列表"""
        resp = self._request('GET',
            f'/console/api/datasets/{dataset_id}/documents',
            params={"page": page, "limit": limit})
        return resp.json() if resp.ok else {}

    def check_indexing_status(self, dataset_id: str) -> Dict[str, int]:
        """检查向量化状态，返回各状态计数"""
        docs = self.get_documents(dataset_id, limit=200)
        status_count: Dict[str, int] = {}
        for doc in docs.get('data', []):
            status = doc.get('display_status', doc.get('indexing_status', 'unknown'))
            status_count[status] = status_count.get(status, 0) + 1
        return status_count

    def wait_for_indexing(self, dataset_id: str) -> bool:
        """等待所有文档向量化完成"""
        log("step", f"等待向量化完成（最长 {VECTORIZE_MAX_WAIT_SEC}s）...")

        start = time.time()
        while True:
            elapsed = int(time.time() - start)
            if elapsed > VECTORIZE_MAX_WAIT_SEC:
                log("warn", f"向量化等待超时 ({VECTORIZE_MAX_WAIT_SEC}s)")
                return False

            status = self.check_indexing_status(dataset_id)
            log("info", f"[{elapsed}s] 状态: {json.dumps(status, ensure_ascii=False)}")

            pending = (status.get('indexing', 0) + status.get('queued', 0) +
                      status.get('pending', 0) + status.get('parsing', 0) +
                      status.get('splitting', 0) + status.get('cleaning', 0))

            if pending == 0 and status.get('completed', 0) > 0:
                log("ok", f"向量化完成! 已完成: {status['completed']}")
                return True

            if status.get('error', 0) > 0:
                log("warn", f"有 {status['error']} 个文档向量化失败")

            time.sleep(VECTORIZE_POLL_SEC)

    # ---------- 工作流操作 ----------

    def get_workflow_draft(self, app_id: str) -> Optional[dict]:
        """获取工作流草稿"""
        resp = self._request('GET',
            f'/console/api/apps/{app_id}/workflows/draft')
        return resp.json() if resp.ok else None

    def sync_workflow_draft(self, app_id: str, graph: dict, features: dict = None,
                            env_vars: list = None, conv_vars: list = None,
                            hash_str: str = None) -> bool:
        """同步/保存工作流草稿"""
        if hash_str is None:
            draft = self.get_workflow_draft(app_id)
            if not draft:
                log("err", "无法获取工作流草稿")
                return False
            hash_str = draft.get('hash', '')
            if features is None:
                features = draft.get('features', {})
            if env_vars is None:
                env_vars = draft.get('environment_variables', [])
            if conv_vars is None:
                conv_vars = draft.get('conversation_variables', [])

        resp = self._request('POST',
            f'/console/api/apps/{app_id}/workflows/draft',
            json={
                "graph": graph,
                "features": features or {},
                "environment_variables": env_vars or [],
                "conversation_variables": conv_vars or [],
                "hash": hash_str
            })

        if resp.ok:
            result = resp.json()
            new_hash = result.get('hash', '?')
            log("ok", f"工作流草稿已同步 (hash: {new_hash[:16]}...)")
            return True
        else:
            log("err", f"工作流草稿同步失败: {resp.status_code} {resp.text[:300]}")
            return False

    def publish_workflow(self, app_id: str,
                         marked_name: str = None,
                         marked_comment: str = None) -> bool:
        """发布工作流"""
        payload = {}
        if marked_name:
            payload['marked_name'] = marked_name
        if marked_comment:
            payload['marked_comment'] = marked_comment

        resp = self._request('POST',
            f'/console/api/apps/{app_id}/workflows/publish',
            json=payload)

        if resp.ok:
            log("ok", "工作流已发布")
            return True
        else:
            log("err", f"工作流发布失败: {resp.status_code} {resp.text[:300]}")
            return False

    def update_workflow_dataset_ids(self, app_id: str,
                                    new_dataset_id: str) -> bool:
        """更新工作流中所有 knowledge-retrieval 节点的 dataset_ids"""
        log("step", f"更新工作流知识库 ID -> {new_dataset_id}")

        draft = self.get_workflow_draft(app_id)
        if not draft or 'graph' not in draft:
            log("err", "无法获取工作流图数据")
            return False

        graph = draft['graph']
        updated_count = 0

        for node in graph.get('nodes', []):
            node_data = node.get('data', {})
            if node_data.get('type') == 'knowledge-retrieval':
                old_ids = node_data.get('dataset_ids', [])
                node_data['dataset_ids'] = [new_dataset_id]
                updated_count += 1
                log("info",
                    f"节点 '{node_data.get('title', node['id'])}' "
                    f"dataset_ids: {old_ids} -> [{new_dataset_id}]")

        if updated_count == 0:
            log("warn", "未找到 knowledge-retrieval 类型节点，"
                "DSL 文件中可能不含 dataset_ids")
            return False

        return self.sync_workflow_draft(
            app_id, graph,
            features=draft.get('features'),
            env_vars=draft.get('environment_variables'),
            conv_vars=draft.get('conversation_variables'),
            hash_str=draft.get('hash')
        )

    # ---------- 应用操作 ----------

    def get_apps(self, page: int = 1, limit: int = 20) -> list:
        """获取应用列表"""
        resp = self._request('GET', '/console/api/apps',
                            params={"page": page, "limit": limit})
        return resp.json().get('data', []) if resp.ok else []

    def get_app(self, app_id: str) -> Optional[dict]:
        """获取应用详情"""
        resp = self._request('GET', f'/console/api/apps/{app_id}')
        return resp.json() if resp.ok else None


# ==================== 主流程 ====================

def deploy_knowledge_base(api: DifyAPI, dataset_id: str = None) -> Optional[str]:
    """S1-T05: 创建知识库并发上传文档"""
    log("step", "=" * 55)
    log("step", "S1-T05: 创建/更新知识库「名著导读-西游记」")
    log("step", "=" * 55)

    # 1. 创建或重用知识库
    if dataset_id:
        ds = api.get_dataset(dataset_id)
        if ds:
            log("ok", f"使用已有知识库: {ds['name']} (ID: {dataset_id})")
        else:
            log("err", f"知识库不存在: {dataset_id}")
            return None
    else:
        dataset_id = api.create_dataset(KB_NAME, KB_DESCRIPTION)
        if not dataset_id:
            return None

    # 2. 配置模型参数
    api.configure_kb_settings(dataset_id)

    # 3. 收集文件并上传
    all_files = collect_files(DATA_DIR)
    if not all_files:
        log("err", "没有文件需要上传")
        return dataset_id

    total = len(all_files)
    for i in range(0, total, BATCH_SIZE):
        batch = all_files[i:i + BATCH_SIZE]
        batch_no = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        log("info", f"批次 {batch_no}/{total_batches}: {len(batch)} 个文件")

        # 上传文件
        file_ids = api.upload_files_batch(batch)
        if not file_ids:
            log("warn", "本批次文件上传全部失败，跳过")
            continue

        # 创建文档
        api.create_documents(dataset_id, file_ids)

        if i + BATCH_SIZE < total:
            log("info", f"等待 {BATCH_UPLOAD_GAP_SEC}s 后处理下一批...")
            time.sleep(BATCH_UPLOAD_GAP_SEC)

    # 4. 等待向量化
    api.wait_for_indexing(dataset_id)

    log("ok", f"S1-T05 完成，Dataset ID = {dataset_id}")
    log("info", "")
    log("info", "=" * 55)
    log("info", f"  Dataset ID = {dataset_id}")
    log("info", "  请妥善保存此 ID，后续可用 --dataset-id 复用")
    log("info", "=" * 55)

    return dataset_id


def deploy_workflow(api: DifyAPI, dataset_id: str, app_id: str = None) -> bool:
    """S1-T06: 更新工作流中的知识库 ID 并发布"""
    log("step", "=" * 55)
    log("step", "S1-T06: 更新工作流并发布")
    log("step", "=" * 55)

    if not app_id:
        app_id = DEFAULT_APP_ID

    # 1. 更新工作流中的 dataset_ids
    if not api.update_workflow_dataset_ids(app_id, dataset_id):
        log("err", "工作流知识库 ID 更新失败")
        return False

    # 2. 发布工作流
    version = datetime.now().strftime("v%Y%m%d-%H%M%S")
    if not api.publish_workflow(app_id,
                                marked_name=version,
                                marked_comment="通过 API 自动部署"):
        log("err", "工作流发布失败")
        return False

    log("ok", "S1-T06 完成，应用已发布")
    return True


def dry_run(api: DifyAPI):
    """干跑模式：验证 API 连接和基本操作"""
    log("step", "干跑模式：验证 API 连接...")

    # 验证登录
    if not api.login():
        log("err", "登录失败")
        return 1

    # 验证知识库 API
    datasets = api.get_datasets()
    log("ok", f"知识库列表: {len(datasets)} 个")
    for ds in datasets[:5]:
        log("info", f"  - {ds['name']} (ID: {ds['id']}, 文档数: {ds.get('document_count', 0)})")

    # 验证应用 API
    apps = api.get_apps()
    log("ok", f"应用列表: {len(apps)} 个")
    for app in apps:
        log("info", f"  - {app['name']} (ID: {app['id']}, Mode: {app['mode']})")
        # 检查工作流草稿
        draft = api.get_workflow_draft(app['id'])
        if draft and draft.get('graph'):
            nodes = draft['graph'].get('nodes', [])
            kb_nodes = [n for n in nodes if n.get('data', {}).get('type') == 'knowledge-retrieval']
            log("info", f"    工作流节点: {len(nodes)} 个, 知识检索节点: {len(kb_nodes)} 个")
            for n in kb_nodes:
                log("info", f"      当前 dataset_ids: {n['data'].get('dataset_ids', [])}")

    # 验证文件收集
    all_files = collect_files(DATA_DIR)
    log("ok", f"待上传文件: {len(all_files)} 个")

    log("ok", "干跑完成")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Dify 平台自动化部署 - 纯 API 版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python dify_deploy.py                              # 创建知识库 + 上传文档 + 更新工作流
  python dify_deploy.py --base-url https://my.dify.io # 自托管
  python dify_deploy.py --skip-knowledge              # 仅更新工作流
  python dify_deploy.py --skip-workflow               # 仅创建知识库
  python dify_deploy.py --dataset-id abc123           # 复用已有知识库
  python dify_deploy.py --app-id xyz456               # 指定应用 ID
  python dify_deploy.py --dry-run                     # 干跑验证
        """,
    )


def main():
    parser = build_arg_parser()
    parser.add_argument("--base-url", default=DIFY_BASE_URL)
    parser.add_argument("--email", default=DIFY_EMAIL)
    parser.add_argument("--password", default=DIFY_PASSWORD)
    parser.add_argument("--dataset-id", default=None)
    parser.add_argument("--app-id", default=None)
    parser.add_argument("--skip-knowledge", action="store_true")
    parser.add_argument("--skip-workflow", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log("info", "=" * 55)
    log("info", "Dify 平台自动化部署脚本 v3.0 (纯 API)")
    log("info", "=" * 55)
    log("info", f"Dify: {args.base_url}")
    log("info", f"账号: {args.email}")

    api = DifyAPI(base_url=args.base_url)

    try:
        # 登录
        if not api.login(args.email, args.password):
            log("err", "登录失败，退出")
            return 1

        # 干跑模式
        if args.dry_run:
            return dry_run(api)

        dataset_id = args.dataset_id
        app_id = args.app_id or DEFAULT_APP_ID

        # ---- S1-T05: 知识库 ----
        if not args.skip_knowledge:
            dataset_id = deploy_knowledge_base(api, dataset_id)
            if not dataset_id:
                log("err", "知识库创建/上传失败")
                return 1
            log("info", "")
        elif dataset_id:
            log("info", f"使用已有知识库: {dataset_id}")
        else:
            log("info", "跳过知识库创建 (--skip-knowledge)")

        # ---- S1-T06: 工作流 ----
        if not args.skip_workflow:
            if not dataset_id:
                log("err", "缺少 dataset_id，无法更新工作流。"
                    "请先创建知识库或通过 --dataset-id 指定")
                return 1
            if not deploy_workflow(api, dataset_id, app_id):
                log("err", "工作流部署失败")
                return 1
        else:
            log("info", "跳过工作流更新 (--skip-workflow)")

        log("ok", "=" * 55)
        log("ok", "全部完成！")
        log("ok", "=" * 55)
        return 0

    except KeyboardInterrupt:
        log("warn", "用户中断")
        return 130
    except Exception as exc:
        log("err", f"执行异常: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
