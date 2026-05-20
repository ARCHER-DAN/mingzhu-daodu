"""查询当前公网访问地址 — 重启电脑后运行"""
import subprocess, os, re, sys

CPOLAR_LOG = os.path.expanduser('~/.cpolar/logs/cpolar_service.log')


def find_url():
    if not os.path.exists(CPOLAR_LOG):
        return None

    out = subprocess.check_output(
        f'grep "名著导读" "{CPOLAR_LOG}" | grep "NewTunnel" | grep "http:" | tail -1',
        shell=True, text=True,
    )
    m = re.search(r'http://[a-z0-9]+\.r18\.vip\.cpolar\.cn', out)
    return m.group(0) if m else None


if __name__ == '__main__':
    url = find_url()
    if url:
        print(f'当前公网地址: {url}')
        print(f'内网地址:     http://your-frontend-server:8080')
    else:
        print('未找到公网地址，请检查 cpolar 是否运行')
        sys.exit(1)
