#!/usr/bin/env python3
"""
Dify API 端到端测试脚本
完整流程: 登录 → 创建知识库 → 上传文件 → 创建文档 → 检查向量化状态
"""
import requests
import json
import os
import sys
import time
import base64
from pathlib import Path

DIFY_BASE = "http://your-dify-server:port"
DIFY_EMAIL = os.environ.get('DIFY_EMAIL', '')
DIFY_PASSWORD = os.environ.get('DIFY_PASSWORD', '')

class DifyAPI:
    """Dify Console API 封装"""

    def __init__(self, base_url: str = DIFY_BASE):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.csrf_token = None
        self._logged_in = False

    def login(self, email: str = DIFY_EMAIL, password: str = DIFY_PASSWORD) -> bool:
        """登录获取会话"""
        encoded_pw = base64.b64encode(password.encode()).decode()

        resp = self.session.post(
            f"{self.base_url}/console/api/login",
            json={"email": email, "password": encoded_pw, "remember_me": True}
        )

        if not resp.ok:
            print(f"[ERROR] 登录失败: {resp.status_code} {resp.text}")
            return False

        # 提取 CSRF token
        for cookie in self.session.cookies:
            if cookie.name == 'csrf_token':
                self.csrf_token = cookie.value
                break

        self._logged_in = True
        print(f"[OK] 登录成功 (CSRF token: {self.csrf_token[:20]}...)")
        return True

    @property
    def headers(self) -> dict:
        return {'X-CSRF-Token': self.csrf_token or ''}

    # ---------- 知识库操作 ----------

    def create_dataset(self, name: str, description: str = "",
                       indexing_technique: str = "high_quality") -> str | None:
        """创建空知识库，返回 dataset_id"""
        resp = self.session.post(
            f"{self.base_url}/console/api/datasets",
            json={
                "name": name,
                "description": description,
                "indexing_technique": indexing_technique,
                "permission": "only_me",
                "provider": "vendor"
            },
            headers=self.headers
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            ds_id = data.get('id')
            print(f"[OK] 知识库创建成功: {name} (ID: {ds_id})")
            return ds_id
        else:
            print(f"[ERROR] 创建知识库失败: {resp.status_code} {resp.text[:300]}")
            return None

    def get_datasets(self, page: int = 1, limit: int = 20) -> list:
        """获取知识库列表"""
        resp = self.session.get(
            f"{self.base_url}/console/api/datasets",
            params={"page": page, "limit": limit},
            headers=self.headers
        )
        data = resp.json()
        return data.get('data', [])

    def update_dataset_setting(self, dataset_id: str, **kwargs):
        """更新知识库设置（embedding, reranker, top_k 等）"""
        resp = self.session.patch(
            f"{self.base_url}/console/api/datasets/{dataset_id}",
            json=kwargs,
            headers=self.headers
        )
        print(f"[INFO] 更新设置: {resp.status_code}")
        return resp.json() if resp.ok else None

    def get_dataset(self, dataset_id: str) -> dict:
        """获取单个知识库详情"""
        resp = self.session.get(
            f"{self.base_url}/console/api/datasets/{dataset_id}",
            headers=self.headers
        )
        return resp.json() if resp.ok else {}

    # ---------- 文件上传 ----------

    def upload_file(self, file_path: str | Path) -> str | None:
        """上传文件到 Dify，返回 file_id"""
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"[ERROR] 文件不存在: {file_path}")
            return None

        file_name = file_path.name
        # 根据扩展名确定 MIME 类型
        mime_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.html': 'text/html',
        }
        mime_type = mime_map.get(file_path.suffix.lower(), 'application/octet-stream')

        with open(file_path, 'rb') as fh:
            resp = self.session.post(
                f"{self.base_url}/console/api/files/upload",
                files={'file': (file_name, fh, mime_type)},
                headers=self.headers
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            file_id = data.get('id')
            print(f"[OK] 文件上传成功: {file_name} (File ID: {file_id})")
            return file_id
        else:
            print(f"[ERROR] 文件上传失败: {resp.status_code} {resp.text[:300]}")
            return None

    def upload_files_batch(self, file_paths: list[Path]) -> list[str]:
        """批量上传文件，返回 file_id 列表"""
        file_ids = []
        total = len(file_paths)
        for i, fp in enumerate(file_paths, 1):
            print(f"[{i}/{total}] ", end="")
            fid = self.upload_file(fp)
            if fid:
                file_ids.append(fid)
            time.sleep(0.5)  # 避免请求过快
        return file_ids

    # ---------- 文档创建 ----------

    def create_document(self, dataset_id: str, file_ids: list[str],
                        indexing_technique: str = "high_quality",
                        process_mode: str = "automatic") -> dict | None:
        """通过 file_ids 在知识库中创建文档"""
        resp = self.session.post(
            f"{self.base_url}/console/api/datasets/{dataset_id}/documents",
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
                "process_rule": {"mode": process_mode},
                "doc_form": "text_model"
            },
            headers=self.headers
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            doc_info = data.get('document', {})
            batch = data.get('batch', '?')
            print(f"[OK] 文档创建成功 (Batch: {batch}, Doc: {doc_info.get('id', '?')})")
            return data
        else:
            print(f"[ERROR] 文档创建失败: {resp.status_code} {resp.text[:500]}")
            return None

    def get_documents(self, dataset_id: str, page: int = 1, limit: int = 50) -> dict:
        """获取知识库文档列表及状态"""
        resp = self.session.get(
            f"{self.base_url}/console/api/datasets/{dataset_id}/documents",
            params={"page": page, "limit": limit},
            headers=self.headers
        )
        return resp.json() if resp.ok else {}

    def check_indexing_status(self, dataset_id: str) -> dict:
        """检查文档向量化状态"""
        docs_data = self.get_documents(dataset_id)
        status_count = {}
        for doc in docs_data.get('data', []):
            status = doc.get('display_status', doc.get('indexing_status', 'unknown'))
            status_count[status] = status_count.get(status, 0) + 1
        return status_count


def run_e2e_test():
    """端到端测试"""
    api = DifyAPI()

    # 1. 登录
    if not api.login():
        return

    # 2. 创建知识库
    kb_name = "名著导读-西游记-API测试"
    kb_desc = "《西游记》原著全文、人物资料、章节概要及文学评论"
    dataset_id = api.create_dataset(kb_name, kb_desc)
    if not dataset_id:
        return

    print(f"\n{'='*50}")
    print(f"知识库 ID: {dataset_id}")
    print(f"{'='*50}\n")

    # 3. 测试上传一个真实文件
    data_dir = Path(r"D:\kaifa\Introduction_Classics\Introduction_Classics_main\data\西游记")
    test_files = list(data_dir.glob("**/*.md"))[:3]  # 取 3 个测试
    if not test_files:
        # 备选：获取 txt 文件
        test_files = list(data_dir.glob("**/*.txt"))[:3]

    if not test_files:
        print("[WARN] 未找到测试文件，跳过文档上传")
        return

    print(f"找到 {len(test_files)} 个测试文件:")
    for f in test_files:
        print(f"  - {f.relative_to(data_dir)}")

    # 4. 上传文件
    file_ids = api.upload_files_batch(test_files)
    if not file_ids:
        print("[ERROR] 所有文件上传失败")
        return

    # 5. 创建文档
    result = api.create_document(dataset_id, file_ids)
    if result:
        print(f"\n[OK] 文档创建完成!")
        print(f"Batch: {result.get('batch', '?')}")

    # 6. 检查向量化状态
    print(f"\n=== 检查向量化状态 ===")
    time.sleep(3)
    status = api.check_indexing_status(dataset_id)
    print(f"状态: {json.dumps(status, ensure_ascii=False)}")

    # 7. 列出知识库
    print(f"\n=== 知识库列表 ===")
    datasets = api.get_datasets()
    for ds in datasets:
        print(f"  - {ds['name']} (ID: {ds['id']}, 文档数: {ds.get('document_count', 0)})")


if __name__ == "__main__":
    run_e2e_test()
