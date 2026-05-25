"""测试 - Sprint 7 失败用例重测（修复后）"""
import requests, time, sys

BASE = 'http://localhost:8080'

print('=== 重测 #16: 422 响应格式 ===')
r = requests.post(f'{BASE}/api/auth/register',
                  json={'email': f'retest_422_{int(time.time())}@test.com'},
                  timeout=5)
body = r.json()
print(f'状态码: {r.status_code}')
print(f'响应: {body}')
passed_16 = r.status_code == 422 and body.get('error','') == '请求参数校验失败'
print(f'结果 #16: {"PASS" if passed_16 else "FAIL"}')

print()
print('=== 重测 #7: login_guard 锁定 ===')
email = f'retest_guard_{int(time.time())}@test.com'
pw = 'WrongPass1'
passed_7 = False
passed_8 = False
passed_9 = False

for i in range(7):
    r = requests.post(f'{BASE}/api/auth/login',
                     json={'email': email, 'password': pw},
                     timeout=5)
    body = r.json()
    err = body.get('error', body.get('detail', ''))
    status = r.status_code
    is_locked = status == 429 and ('过于频繁' in err or '分' in err)
    print(f'请求{i+1}: status={status}, error={err[:80]}')
    if is_locked:
        print(f'  >> login_guard 锁定触发于第{i+1}次请求!')
        passed_7 = True

        has_time = '分' in err and '秒' in err
        passed_8 = has_time
        print(f'  #8 (时间信息): {"PASS" if has_time else "FAIL"}')

        r9 = requests.post(f'{BASE}/api/auth/login',
                          json={'email': email, 'password': 'SomeCorrect1'},
                          timeout=5)
        body9 = r9.json()
        err9 = body9.get('error', body9.get('detail', ''))
        passed_9 = r9.status_code == 429
        print(f'  正确密码登录: status={r9.status_code}, error={err9[:80]}')
        print(f'  #9: {"PASS" if passed_9 else "FAIL"}')
        break

if not passed_7:
    print('>> 7次请求后login_guard均未触发锁定!')

print()
print(f'#16: {"PASS" if passed_16 else "FAIL"}')
print(f'#7:  {"PASS" if passed_7 else "FAIL"}')
print(f'#8:  {"PASS" if passed_8 else "FAIL"}')
print(f'#9:  {"PASS" if passed_9 else "FAIL"}')

all_pass = passed_16 and passed_7 and passed_8 and passed_9
print(f'\n修复后全部通过: {"YES" if all_pass else "NO"}')
sys.exit(0 if all_pass else 1)
