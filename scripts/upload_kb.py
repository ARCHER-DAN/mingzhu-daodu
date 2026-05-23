"""批量上传四大名著到 Dify 知识库"""
import os, sys, time, base64, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend.config import env

DIFY_BASE = env('DIFY_BASE_URL')
EMAIL = env('DIFY_EMAIL')
PASSWORD = env('DIFY_PASSWORD')
DATASET_ID = '32cc43c3-1598-4dbd-bfd1-a6d01b3837bc'

sess = requests.Session()
encoded = base64.b64encode(PASSWORD.encode()).decode()
r = sess.post(f'{DIFY_BASE}/console/api/login',
              json={'email': EMAIL, 'password': encoded, 'remember_me': True})
if not r.ok:
    print(f'登录失败: {r.status_code}')
    sys.exit(1)
csrf = [c.value for c in sess.cookies if c.name == 'csrf_token'][0]
print(f'登录成功, CSRF={csrf[:20]}...')

uploaded = 0
for novel in ['西游记', '三国演义', '水浒传', '红楼梦']:
    src_dir = os.path.join(ROOT, 'data', novel, '01_原著原文')
    if not os.path.exists(src_dir):
        continue
    files = sorted(os.listdir(src_dir))
    print(f'\n{novel}: {len(files)} 文件')
    for fname in files:
        fpath = os.path.join(src_dir, fname)
        try:
            # Upload file
            with open(fpath, 'rb') as fh:
                r = sess.post(f'{DIFY_BASE}/console/api/files/upload',
                             files={'file': (fname, fh, 'text/plain')},
                             headers={'X-CSRF-Token': csrf})
            if not r.ok:
                print(f'  上传失败 {fname}: {r.status_code}')
                continue
            file_id = r.json()['id']

            # Create document
            r = sess.post(f'{DIFY_BASE}/console/api/datasets/{DATASET_ID}/documents',
                         json={
                             'data_source': {
                                 'type': 'upload_file',
                                 'info_list': {
                                     'data_source_type': 'upload_file',
                                     'file_info_list': {'file_ids': [file_id]}
                                 }
                             },
                             'indexing_technique': 'high_quality',
                             'process_rule': {'mode': 'automatic'},
                             'doc_form': 'text_model'
                         },
                         headers={'X-CSRF-Token': csrf})
            if r.ok:
                uploaded += 1
                if uploaded % 10 == 0:
                    print(f'  已上传 {uploaded} / {len(files)}')
            else:
                print(f'  创建文档失败 {fname}: {r.status_code}')
        except Exception as e:
            print(f'  错误 {fname}: {e}')
        time.sleep(0.5)  # 避免限流

print(f'\n上传完成: {uploaded} 个文档')
print('等待 Dify 向量化处理...')
