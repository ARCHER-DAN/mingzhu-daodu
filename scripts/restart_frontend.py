"""前端服务重启脚本 —— 不碰 cpolar，保持公网域名不变"""
import subprocess, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVE_SCRIPT = os.path.join(ROOT, 'scripts', 'serve_frontend.py')


def kill_existing():
    try:
        out = subprocess.check_output(
            'netstat -ano | findstr ":8080.*LISTENING"', shell=True, text=True
        )
        pid = out.strip().split()[-1]
        subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
        print(f'已停止旧进程 PID={pid}')
        time.sleep(1)
    except subprocess.CalledProcessError:
        print('无旧进程')


def start_server():
    env = os.environ.copy()
    env.setdefault('PYTHONPATH', ROOT)
    subprocess.Popen(
        [sys.executable, SERVE_SCRIPT],
        cwd=ROOT, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(2)
    print('前端服务已启动')


def verify():
    import urllib.request
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:8080', timeout=5)
        print(f'验证: http://127.0.0.1:8080 -> {resp.status}')
    except Exception as e:
        print(f'验证失败: {e}')


if __name__ == '__main__':
    kill_existing()
    start_server()
    verify()
    print('\ncpolar 未重启，公网域名不变。')
