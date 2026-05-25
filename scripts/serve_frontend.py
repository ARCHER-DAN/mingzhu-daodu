"""前端生产服务器 — 静态文件 + API 代理 + 认证"""
import http.server
import urllib.request
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import init_db
from backend.auth import register_user, login_user, verify_token, get_user_by_id, create_token

DIFY_API = 'http://your-dify-server:port/v1'
DIFY_API_KEY = os.environ.get('DIFY_APP_API_KEY', '')
PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

import re

def _list_chapters(book):
    """扫描书籍原文目录，返回章节列表"""
    book_dir = os.path.join(DATA_DIR, book, '01_原著原文')
    if not os.path.isdir(book_dir):
        return []
    chapters = []
    for fname in sorted(os.listdir(book_dir)):
        if not fname.endswith('.txt'):
            continue
        m = re.match(r'^第(\d+)回_(.+)\.txt$', fname)
        if m:
            chapters.append({'id': int(m.group(1)), 'title': m.group(2).replace('_', ''), 'filename': fname})
    return chapters


def _read_chapter(book, filename):
    """读取指定章节全文"""
    path = os.path.join(DATA_DIR, book, '01_原著原文', filename)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.read().strip()


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _json_response(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length))

    def do_POST(self):
        if self.path == '/api/auth/register':
            self._handle_register()
        elif self.path == '/api/auth/login':
            self._handle_login()
        elif self.path.startswith('/api/'):
            self._proxy_dify()
        else:
            super().do_POST()

    def do_GET(self):
        if self.path == '/api/auth/me':
            self._handle_me()
        elif self.path.startswith('/api/chapters'):
            self._handle_chapters()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def _handle_register(self):
        body = self._read_body()
        email = body.get('email', '').strip()
        password = body.get('password', '')
        display_name = body.get('display_name', '').strip()
        if not email or not password:
            return self._json_response({'error': '邮箱和密码不能为空'}, 400)
        if len(password) < 6:
            return self._json_response({'error': '密码至少6位'}, 400)
        user = register_user(email, password, display_name or None)
        if user is None:
            return self._json_response({'error': '该邮箱已注册'}, 409)
        user['token'] = create_token(user)
        self._json_response(user, 201)

    def _handle_login(self):
        body = self._read_body()
        email = body.get('email', '').strip()
        password = body.get('password', '')
        if not email or not password:
            return self._json_response({'error': '邮箱和密码不能为空'}, 400)
        user = login_user(email, password)
        if user is None:
            return self._json_response({'error': '邮箱或密码错误'}, 401)
        user['token'] = create_token(user)
        self._json_response(user)

    def _handle_me(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return self._json_response({'error': '未登录'}, 401)
        payload = verify_token(auth[7:])
        if not payload:
            return self._json_response({'error': '登录已过期'}, 401)
        user = get_user_by_id(payload['user_id'])
        if not user:
            return self._json_response({'error': '用户不存在'}, 404)
        self._json_response(user)

    def _handle_chapters(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        book = qs.get('book', [None])[0]
        chapter_id = qs.get('chapter', [None])[0]

        if not book:
            return self._json_response({'error': '缺少 book 参数'}, 400)

        chapters = _list_chapters(book)
        if not chapters:
            return self._json_response({'error': f'书籍 {book} 原文数据不存在'}, 404)

        if chapter_id:
            ch = next((c for c in chapters if c['id'] == int(chapter_id)), None)
            if not ch:
                return self._json_response({'error': f'第{chapter_id}回不存在'}, 404)
            content = _read_chapter(book, ch['filename'])
            if content is None:
                return self._json_response({'error': '章节文件读取失败'}, 500)
            return self._json_response({'id': ch['id'], 'title': ch['title'], 'content': content})

        return self._json_response({'book': book, 'chapters': chapters})

    def _proxy_dify(self):
        target = DIFY_API + self.path[4:]
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''

        req = urllib.request.Request(target, data=body, method='POST')
        for k, v in self.headers.items():
            if k.lower() in ('host', 'content-length', 'authorization'):
                continue
            req.add_header(k, v)
        if DIFY_API_KEY:
            req.add_header('Authorization', f'Bearer {DIFY_API_KEY}')

        try:
            resp = urllib.request.urlopen(req, timeout=60)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(k, v)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self._json_response({'error': 'Dify 服务不可达: ' + str(e)}, 502)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    init_db()
    from backend.init_admin import init_admin
    init_admin()
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    print('名著导读前端已启动')
    print('  前端:    http://your-frontend-server:{}'.format(PORT))
    print('  API代理: /api/* -> {}'.format(DIFY_API))
    print('  认证:    /api/auth/register, /api/auth/login, /api/auth/me')
    server.serve_forever()
