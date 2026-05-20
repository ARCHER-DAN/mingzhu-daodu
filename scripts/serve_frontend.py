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
PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')


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

    def _proxy_dify(self):
        target = DIFY_API + self.path[4:]
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''

        req = urllib.request.Request(target, data=body, method='POST')
        for k, v in self.headers.items():
            if k.lower() in ('host', 'content-length'):
                continue
            req.add_header(k, v)

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
