#!/usr/bin/env python3
"""
Dify API 测试脚本 - 测试 Console API 的文档上传流程
"""
import requests
import json
import os
import sys
import base64

DIFY_BASE = "http://your-dify-server:port"
DIFY_EMAIL = os.environ.get('DIFY_EMAIL', '')
DIFY_PASSWORD = os.environ.get('DIFY_PASSWORD', '')

def login() -> tuple:
    """登录 Dify Console API，返回 (cookies_dict, csrf_token)"""
    encoded_pw = base64.b64encode(DIFY_PASSWORD.encode()).decode()

    sess = requests.Session()
    resp = sess.post(
        f"{DIFY_BASE}/console/api/login",
        json={"email": DIFY_EMAIL, "password": encoded_pw, "remember_me": True}
    )
    if not resp.ok:
        print(f"登录失败: {resp.status_code} {resp.text}")
        sys.exit(1)

    print(f"登录成功: {resp.json()}")

    # 提取 CSRF token
    csrf_token = None
    for cookie in sess.cookies:
        if cookie.name == 'csrf_token':
            csrf_token = cookie.value
            break

    print(f"CSRF Token: {csrf_token[:30] if csrf_token else 'MISSING'}...")
    return sess, csrf_token

def upload_file(session: requests.Session, csrf_token: str, file_path: str) -> str:
    """上传文件到 Dify，返回 file_id"""
    print(f"\n=== 上传文件: {file_path} ===")
    file_name = os.path.basename(file_path)

    with open(file_path, 'rb') as fh:
        resp = session.post(
            f"{DIFY_BASE}/console/api/files/upload",
            files={'file': (file_name, fh, 'application/octet-stream')},
            headers={'X-CSRF-Token': csrf_token}
        )

    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")

    if not resp.ok:
        return None

    data = resp.json()
    return data.get('id')

def create_document(session: requests.Session, csrf_token: str,
                    dataset_id: str, file_id: str) -> dict:
    """通过 file_id 在知识库中创建文档"""
    print(f"\n=== 创建文档: dataset={dataset_id}, file={file_id} ===")

    doc_data = {
        "original_document_id": file_id,
        "indexing_technique": "high_quality",
        "process_rule": {"mode": "automatic"},
        "doc_form": "text_model"
    }

    resp = session.post(
        f"{DIFY_BASE}/console/api/datasets/{dataset_id}/documents",
        json=doc_data,
        headers={'X-CSRF-Token': csrf_token}
    )

    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:1000]}")

    return resp.json() if resp.ok else None

def create_dataset(session: requests.Session, csrf_token: str,
                   name: str, description: str = "") -> str:
    """创建空知识库"""
    print(f"\n=== 创建知识库: {name} ===")

    resp = session.post(
        f"{DIFY_BASE}/console/api/datasets",
        json={
            "name": name,
            "description": description,
            "indexing_technique": "high_quality",
            "permission": "only_me",
            "provider": "vendor"
        },
        headers={'X-CSRF-Token': csrf_token}
    )

    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"ID: {data.get('id')}, Name: {data.get('name')}")

    return data.get('id') if resp.ok else None

def list_documents(session: requests.Session, csrf_token: str, dataset_id: str):
    """列出知识库中的文档"""
    print(f"\n=== 文档列表: dataset={dataset_id} ===")

    resp = session.get(
        f"{DIFY_BASE}/console/api/datasets/{dataset_id}/documents",
        params={"page": 1, "limit": 10},
        headers={'X-CSRF-Token': csrf_token}
    )

    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Total: {data.get('total', 0)}, Documents: {len(data.get('data', []))}")
    for doc in data.get('data', [])[:5]:
        print(f"  - {doc.get('name')}: {doc.get('display_status', doc.get('indexing_status', '?'))}")

    return data

if __name__ == "__main__":
    # 登录
    session, csrf_token = login()

    # 创建新知识库
    dataset_id = create_dataset(session, csrf_token, "API完整测试-西游记", "由脚本通过API创建")

    if not dataset_id:
        print("知识库创建失败")
        sys.exit(1)

    # 创建测试文件
    test_file = os.path.join(os.path.dirname(__file__), "_test_upload.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("这是通过Dify API上传的测试文档。\n")
        f.write("《西游记》是中国古典四大名著之一。\n")
        f.write("作者：吴承恩\n")

    # 上传文件
    file_id = upload_file(session, csrf_token, test_file)

    if file_id:
        # 创建文档
        result = create_document(session, csrf_token, dataset_id, file_id)
        if result:
            print(f"\n*** 成功! 文档已创建: {result.get('document', {}).get('id', 'N/A')} ***")
            print(f"知识库 ID: {dataset_id}")

    # 列出文档
    list_documents(session, csrf_token, dataset_id)

    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
