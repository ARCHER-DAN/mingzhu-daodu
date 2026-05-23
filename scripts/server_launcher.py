"""名著导读 — 服务启动器
cpolar 账号登录 → 获取全部隧道 → 手动选择 → 启动服务
"""
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import sys
import re
import time
import json
import urllib.request
import threading
import yaml

if getattr(sys, 'frozen', False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA_FILE = os.path.join(ROOT, 'android', 'app', 'src', 'main', 'java', 'com', 'mingzhu', 'app', 'MainActivity.java')
SERVE_SCRIPT = os.path.join(ROOT, 'scripts', 'serve_frontend.py')
VENV_PYTHON = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
CPOLAR_YML = os.path.join(os.path.expanduser('~'), '.cpolar', 'cpolar.yml')
SAVED_CREDS = os.path.join(ROOT, '.launcher_creds.json')

CPOLAR_LOCAL_API = 'http://127.0.0.1:4040'

server_process = None


# ═══════════════════════════════════════════════
# 凭据管理
# ═══════════════════════════════════════════════

def load_saved_creds():
    try:
        with open(SAVED_CREDS, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_creds(email, password, remember):
    if remember:
        with open(SAVED_CREDS, 'w') as f:
            json.dump({'email': email, 'password': password}, f)
    else:
        try:
            os.remove(SAVED_CREDS)
        except Exception:
            pass


# ═══════════════════════════════════════════════
# cpolar 配置操作
# ═══════════════════════════════════════════════

def _read_cpolar_config():
    try:
        with open(CPOLAR_YML, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _write_cpolar_config(config):
    try:
        with open(CPOLAR_YML, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception:
        return False


def _restart_cpolar_service():
    """重启 cpolar 服务"""
    try:
        subprocess.run('net stop "cpolarService"', shell=True, capture_output=True, timeout=15)
        time.sleep(3)
        subprocess.run('net start "cpolarService"', shell=True, capture_output=True, timeout=15)
        time.sleep(6)
        return True
    except Exception:
        pass

    # fallback: 直接杀进程
    try:
        subprocess.run('taskkill /F /IM cpolar.exe', shell=True, capture_output=True, timeout=5)
        time.sleep(2)
        # 重新启动
        config = _read_cpolar_config()
        if config:
            subprocess.Popen(
                ['G:\\zhuangzai\\cpolar\\cpolar.exe', 'start-all', '-daemon=on', '-dashboard=on',
                 f'-log=C:\\Users\\Administrator\\.cpolar\\logs\\cpolar_service.log',
                 f'-config={CPOLAR_YML}'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(6)
            return True
    except Exception:
        pass
    return False


def enable_inspection_for_all():
    """为所有 cpolar 隧道启用 inspection"""
    config = _read_cpolar_config()
    if not config:
        return False

    tunnels = config.get('tunnels', {})
    if not tunnels:
        return False

    changed = False
    for name, cfg in tunnels.items():
        if isinstance(cfg, dict) and cfg.get('inspect') != 'true':
            cfg['inspect'] = 'true'
            changed = True

    if changed:
        if _write_cpolar_config(config):
            _restart_cpolar_service()
            return True
    return False


# ═══════════════════════════════════════════════
# 隧道检测
# ═══════════════════════════════════════════════

def fetch_all_tunnels():
    """
    从本地 cpolar Web 检查页面获取所有隧道信息。
    REST API (/api/tunnels) 在 cpolar v3 中返回空 body，
    但 /http/in 页面的 window.data 中包含完整隧道数据。
    返回 [(名称, 公网URL, 本地地址), ...]，去重，优先 HTTPS
    """
    try:
        req = urllib.request.Request(f'{CPOLAR_LOCAL_API}/http/in')
        resp = urllib.request.urlopen(req, timeout=5)
        html = resp.read().decode('utf-8', errors='replace')

        # window.data = JSON.parse("...\"...")，内部 \" 是转义引号
        # 找到 JSON.parse(" 的位置，手动提取完整 JSON 字符串
        start_marker = 'JSON.parse("'
        pos = html.find(start_marker)
        if pos < 0:
            return []

        pos += len(start_marker)
        # 从 pos 开始找匹配的 ")，跳过内部的 \"
        i = pos
        while i < len(html) - 1:
            if html[i] == '\\' and html[i+1] == '"':
                i += 2  # 跳过转义引号
                continue
            if html[i] == '"' and html[i+1] == ')':
                json_str = html[pos:i]
                break
            i += 1
        else:
            return []

        raw = json_str.replace('\\\\', '\\').replace('\\"', '"')
        data = json.loads(raw)

        seen = set()
        result = []
        for t in data.get('UiState', {}).get('Tunnels', []):
            name = t.get('Name', '未知')
            pub_url = t.get('PublicUrl', '')
            local_addr = t.get('LocalAddr', '')
            addr = local_addr.replace('http://', '').replace('https://', '').replace('localhost', '127.0.0.1')
            tid = t.get('ID', '')
            # 去重：同 ID 优先保留 HTTPS
            existing = [i for i, r in enumerate(result) if r[3] == tid]
            if existing:
                if pub_url.startswith('https'):
                    result[existing[0]] = (name, pub_url, addr, tid)
            else:
                result.append((name, pub_url, addr, tid))
        return [(name, url, addr) for name, url, addr, _tid in result]
    except Exception:
        pass

    return []


def get_all_cpolar_tunnels():
    """
    获取所有 cpolar 隧道：
    1. 先尝试直接获取（inspect 可能已开启）
    2. 如果获取不到，则启用 inspect 并重启 cpolar，再获取
    """
    tunnels = fetch_all_tunnels()
    if tunnels:
        return tunnels

    # 没有获取到，尝试启用 inspection
    if enable_inspection_for_all():
        tunnels = fetch_all_tunnels()
    return tunnels


# ═══════════════════════════════════════════════
# URL 管理
# ═══════════════════════════════════════════════

def get_current_url():
    try:
        with open(JAVA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'loadUrl\("([^"]+)"\)', content)
        if m:
            return m.group(1).replace('?from=app', '')
    except Exception:
        pass
    return ''


def update_url(new_url):
    if '?from=app' in new_url:
        new_url = new_url.replace('?from=app', '')
    full_url = new_url.rstrip('/') + '?from=app'

    with open(JAVA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    updated = re.sub(r'loadUrl\("[^"]+"\)', f'loadUrl("{full_url}")', content)
    if updated == content:
        return False
    with open(JAVA_FILE, 'w', encoding='utf-8') as f:
        f.write(updated)
    return True


# ═══════════════════════════════════════════════
# 服务管理
# ═══════════════════════════════════════════════

def kill_existing():
    global server_process
    try:
        out = subprocess.check_output(
            'netstat -ano | findstr ":8080.*LISTENING"', shell=True, text=True
        )
        pid = out.strip().split()[-1]
        subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
        time.sleep(1)
    except subprocess.CalledProcessError:
        pass


def start_server():
    global server_process
    kill_existing()

    python_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    env = os.environ.copy()
    env.setdefault('PYTHONPATH', ROOT)

    server_process = subprocess.Popen(
        [python_exe, SERVE_SCRIPT],
        cwd=ROOT, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(2)

    try:
        resp = urllib.request.urlopen('http://127.0.0.1:8080', timeout=5)
        return resp.status == 200
    except Exception:
        return False


# ═══════════════════════════════════════════════
# GUI 事件处理
# ═══════════════════════════════════════════════

def on_login():
    """登录 cpolar：保存凭据 → 启用 inspection → 列出全部隧道"""
    email = email_var.get().strip()
    password = pwd_var.get().strip()
    remember = remember_var.get()

    if not email or not password:
        messagebox.showwarning('提示', '请输入 cpolar 账号和密码')
        return

    save_creds(email, password, remember)

    status_text.set('正在连接 cpolar 并获取隧道列表...')
    progress.start()
    login_frame['text'] = 'Step 1: cpolar 登录 — 正在连接...'
    root.update()

    tunnels = get_all_cpolar_tunnels()

    progress.stop()
    login_frame['text'] = 'Step 1: cpolar 登录'

    if tunnels:
        populate_tunnel_list(tunnels)
        status_text.set(f'已连接 — {email} — 找到 {len(tunnels)} 个隧道')
        login_btn.config(text='重新登录/刷新隧道', bg='#6B8E23')
    else:
        status_text.set(f'未获取到隧道 — {email}，请检查 cpolar 服务')
        messagebox.showwarning('提示',
            f'已连接账号 {email}，但未获取到隧道列表。\n\n'
            '请确认:\n'
            '1. cpolar 服务正在运行\n'
            '2. 隧道配置中存在活跃隧道\n'
            '3. 或者手动在下方输入公网地址')


def populate_tunnel_list(tunnels):
    """填充隧道下拉列表"""
    tunnel_choices = []
    for name, url, addr in tunnels:
        label = f'{name} → {url} ({addr})'
        tunnel_choices.append(label)

    tunnel_combo['values'] = tunnel_choices
    if tunnel_choices:
        tunnel_combo.current(0)
        # 优先选 8080
        for i, (name, url, addr) in enumerate(tunnels):
            if '8080' in addr:
                tunnel_combo.current(i)
                break
        on_tunnel_select()


def on_tunnel_select(event=None):
    """选了隧道后自动填入公网 URL"""
    selected = tunnel_var.get()
    if not selected:
        return
    # 从 "名称 → URL (proto://addr)" 中提取 URL
    parts = selected.split(' → ')
    if len(parts) >= 2:
        url_part = parts[1].split(' (')[0].strip()
        url_var.set(url_part)


def on_save_and_start():
    url = url_var.get().strip()
    if not url:
        messagebox.showwarning('提示', '请先选择隧道或手动输入公网地址')
        return

    if not url.startswith('http'):
        url = 'https://' + url

    status_text.set('正在更新公网地址...')
    root.update()

    changed = update_url(url)
    status_text.set(f'公网地址{"已更新" if changed else "未变化"}: {url}')
    root.update()

    status_text.set('正在启动本地服务...')
    root.update()
    ok = start_server()

    if ok:
        status_text.set(f'服务已启动 — http://127.0.0.1:8080 | 公网: {url}')
        messagebox.showinfo('成功', f'服务已启动\n本地: http://127.0.0.1:8080\n公网: {url}')
    else:
        status_text.set('服务启动失败')
        messagebox.showerror('失败', '服务启动失败')


def on_start_only():
    status_text.set('正在启动本地服务...')
    root.update()
    ok = start_server()
    if ok:
        status_text.set('服务已启动 — http://127.0.0.1:8080')
        messagebox.showinfo('成功', '服务已启动 http://127.0.0.1:8080')
    else:
        status_text.set('服务启动失败')
        messagebox.showerror('失败', '服务启动失败')


def on_threaded(func):
    threading.Thread(target=func, daemon=True).start()


# ═══════════════════════════════════════════════
# GUI 布局
# ═══════════════════════════════════════════════

root = tk.Tk()
root.title('名著导读 — 服务启动器')
root.geometry('600x460')
root.resizable(False, False)
root.configure(bg='#FAF7F2')

root.update_idletasks()
w, h = root.winfo_width(), root.winfo_height()
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry(f'+{(sw-w)//2}+{(sh-h)//2}')

tk.Label(root, text='名著导读 服务启动器', font=('Microsoft YaHei', 14, 'bold'),
         bg='#FAF7F2', fg='#2C1810').pack(pady=(16, 5))
tk.Label(root, text='cpolar 登录 → 获取全部隧道 → 选择 → 启动', fg='#7B6B5A', bg='#FAF7F2').pack()

# ── Step 1: cpolar 登录 ──
login_frame = tk.LabelFrame(root, text='Step 1: cpolar 登录', bg='#FAF7F2',
                            font=('Microsoft YaHei', 10, 'bold'), fg='#6B3A2A')
login_frame.pack(pady=(12, 4), padx=30, fill='x')

creds = load_saved_creds()

row1 = tk.Frame(login_frame, bg='#FAF7F2')
row1.pack(fill='x', padx=12, pady=(8, 4))
tk.Label(row1, text='邮箱:', width=6, anchor='e', bg='#FAF7F2').pack(side='left')
email_var = tk.StringVar(value=creds.get('email', ''))
tk.Entry(row1, textvariable=email_var, font=('Microsoft YaHei', 10), width=32).pack(side='left', padx=4)

row2 = tk.Frame(login_frame, bg='#FAF7F2')
row2.pack(fill='x', padx=12, pady=(2, 4))
tk.Label(row2, text='密码:', width=6, anchor='e', bg='#FAF7F2').pack(side='left')
pwd_var = tk.StringVar(value=creds.get('password', ''))
tk.Entry(row2, textvariable=pwd_var, font=('Microsoft YaHei', 10), width=32, show='*').pack(side='left', padx=4)

row3 = tk.Frame(login_frame, bg='#FAF7F2')
row3.pack(fill='x', padx=12, pady=(0, 8))
remember_var = tk.BooleanVar(value=bool(creds.get('email')))
tk.Checkbutton(row3, text='记住密码', variable=remember_var, bg='#FAF7F2').pack(side='left')
login_btn = tk.Button(row3, text='登录 cpolar（获取全部隧道）',
                      command=lambda: on_threaded(on_login),
                      bg='#D4A017', fg='white', font=('Microsoft YaHei', 10, 'bold'),
                      padx=16, pady=4, border=0, cursor='hand2')
login_btn.pack(side='right')

# ── Step 2: 选择隧道 ──
tunnel_frame = tk.LabelFrame(root, text='Step 2: 选择隧道', bg='#FAF7F2',
                             font=('Microsoft YaHei', 10, 'bold'), fg='#6B3A2A')
tunnel_frame.pack(pady=(4, 4), padx=30, fill='x')

sel_row = tk.Frame(tunnel_frame, bg='#FAF7F2')
sel_row.pack(fill='x', padx=12, pady=8)

tk.Label(sel_row, text='隧道:', width=5, anchor='e', bg='#FAF7F2').pack(side='left')
tunnel_var = tk.StringVar()
tunnel_combo = ttk.Combobox(sel_row, textvariable=tunnel_var, font=('Microsoft YaHei', 9),
                            state='readonly', width=52)
tunnel_combo.pack(side='left', padx=4)
tunnel_combo.bind('<<ComboboxSelected>>', on_tunnel_select)

url_row = tk.Frame(tunnel_frame, bg='#FAF7F2')
url_row.pack(fill='x', padx=12, pady=(0, 8))
tk.Label(url_row, text='公网:', width=5, anchor='e', bg='#FAF7F2').pack(side='left')
url_var = tk.StringVar(value=get_current_url())
tk.Entry(url_row, textvariable=url_var, font=('Consolas', 10), width=52).pack(side='left', padx=4)

# ── Step 3: 启动服务 ──
start_frame = tk.LabelFrame(root, text='Step 3: 启动服务', bg='#FAF7F2',
                            font=('Microsoft YaHei', 10, 'bold'), fg='#6B3A2A')
start_frame.pack(pady=(4, 8), padx=30, fill='x')

btn_row = tk.Frame(start_frame, bg='#FAF7F2')
btn_row.pack(pady=8)

tk.Button(btn_row, text='保存公网地址并启动服务', command=lambda: on_threaded(on_save_and_start),
          bg='#6B3A2A', fg='white', font=('Microsoft YaHei', 10),
          padx=16, pady=6, border=0, cursor='hand2').pack(side='left', padx=4)
tk.Button(btn_row, text='仅启动服务', command=lambda: on_threaded(on_start_only),
          font=('Microsoft YaHei', 10), padx=16, pady=6,
          cursor='hand2', bg='#d4c4a8', border=0).pack(side='left', padx=4)

# ── 进度条 ──
progress = ttk.Progressbar(root, mode='indeterminate')
progress.pack(fill='x', padx=30, pady=(0, 4))

# ── 状态栏 ──
status_text = tk.StringVar(value='就绪 — 输入 cpolar 账号密码，点击登录')
status = tk.Label(root, textvariable=status_text, relief='sunken',
                  anchor='w', font=('Microsoft YaHei', 9), fg='#555')
status.pack(side='bottom', fill='x')

# 如果有保存的凭据，启动时自动登录
if creds.get('email') and creds.get('password'):
    root.after(500, lambda: on_threaded(on_login))

root.mainloop()
