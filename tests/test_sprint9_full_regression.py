"""
测试 - Sprint 9 全量回归测试 S9-10
======================================
4 个 Sprint (S6~S9) 累计功能的总验收测试。
测试目标：确认 V3.0.0 是否满足发布标准。

执行前确保：uvicorn server.main:app --port 8080 已启动

测试覆盖 (25+ 用例)：
  一、核心 API 回归 (8 端点)
  二、Sprint 9 管理员 + 静态文件
  三、Sprint 8 数据功能回归
  四、Sprint 7 安全功能回归 (含注入/XSS)

注意：安全测试（限流/锁定）最后执行，避免耗尽配额影响其他测试。
"""
import requests
import json
import time
import sys
import os

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8080"

# ============================================================================
# 全局状态
# ============================================================================
PASS = 0
FAIL = 0
results = []
TEST_EMAIL_BASE = f"s9reg_{int(time.time())}"
TOKEN = None
ADMIN_TOKEN = None

from server.config import ADMIN_EMAIL, ADMIN_PASSWORD


def record(test_id, name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
    else:
        FAIL += 1
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] #{test_id} {name}"
    if detail:
        line += f"\n       {detail}"
    results.append(line)
    print(line)


def hdr(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ============================================================================
# 一、核心 API 回归 (用例 1-8)
# ============================================================================

def test_core_api():
    hdr("一、核心 API 回归 (用例 1-8)")
    global TOKEN

    # --- 1. 健康检查 ---
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    ok = r.status_code == 200 and r.json().get("status") == "ok"
    record(1, "GET /api/health -> 200 + status=ok", ok,
           f"status={r.status_code}, body={r.json()}")

    # --- 2. books 列表 ---
    r = requests.get(f"{BASE_URL}/api/chapters/books", timeout=5)
    books = r.json().get("books", [])
    expected = {"西游记", "三国演义", "红楼梦", "水浒传"}
    ok = r.status_code == 200 and set(books) == expected and len(books) == 4
    record(2, "GET /api/chapters/books -> 200 + 4本书", ok,
           f"books={books}" if not ok else str(books))

    # --- 3. 章节目录 ---
    r = requests.get(f"{BASE_URL}/api/chapters", params={"book": "西游记"}, timeout=5)
    chapters = r.json().get("chapters", [])
    ok = r.status_code == 200 and len(chapters) == 100
    record(3, "GET /api/chapters?book=西游记 -> 100回", ok,
           f"status={r.status_code}, count={len(chapters)}")

    # --- 4. 章节正文 ---
    r = requests.get(f"{BASE_URL}/api/chapters",
                     params={"book": "西游记", "chapter": 1}, timeout=5)
    data = r.json()
    content = data.get("content", "")
    title = data.get("title", "")
    ok = r.status_code == 200 and len(content) > 100 and len(title) > 0
    record(4, "GET /api/chapters?book=西游记&chapter=1 -> 正文非空", ok,
           f"title={title[:20]}..., len={len(content)}")

    # --- 5. 注册 ---
    reg_email = f"{TEST_EMAIL_BASE}_core@test.com"
    reg_password = "TestPass123"

    # 正常注册
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": reg_email, "password": reg_password,
                            "display_name": "回归测试"}, timeout=5)
    ok = r.status_code in (200, 201) and "token" in r.json()
    detail = f"status={r.status_code}"
    if ok:
        TOKEN = r.json().get("token", "")
        detail += f", token={'OK' if TOKEN else 'MISSING'}"
    else:
        detail += f", body={r.text[:80]}"
    record(5, "POST /api/auth/register -> 201 + token", ok, detail)

    # 重复注册 -> 409
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": reg_email, "password": reg_password}, timeout=5)
    ok = r.status_code == 409
    record(5.1, "POST /api/auth/register(重复) -> 409", ok,
           f"status={r.status_code}, msg={r.json().get('error','')[:50]}")

    # 缺字段 -> 422
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": f"{TEST_EMAIL_BASE}_nopass@test.com"}, timeout=5)
    ok = r.status_code == 422
    record(5.2, "POST /api/auth/register(缺字段) -> 422", ok,
           f"status={r.status_code}")

    # --- 6. 登录 ---
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": reg_email, "password": reg_password}, timeout=5)
    ok = r.status_code == 200 and "token" in r.json()
    if ok:
        TOKEN = r.json().get("token", TOKEN)
    record(6, "POST /api/auth/login -> 200 + token", ok,
           f"status={r.status_code}")

    # 错误密码 -> 401
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": reg_email, "password": "WrongPassword1"}, timeout=5)
    ok = r.status_code == 401
    record(6.1, "POST /api/auth/login(错密码) -> 401", ok,
           f"status={r.status_code}")

    # --- 7. /auth/me ---
    if TOKEN:
        r = requests.get(f"{BASE_URL}/api/auth/me",
                         headers={"Authorization": f"Bearer {TOKEN}"}, timeout=5)
        ok = r.status_code == 200 and "email" in r.json()
        record(7, "GET /api/auth/me(有token) -> 200", ok,
               f"status={r.status_code}")
    else:
        record(7, "GET /api/auth/me(有token) -> 200", False, "无token")

    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=5)
    ok = r.status_code == 401
    record(7.1, "GET /api/auth/me(无token) -> 401", ok,
           f"status={r.status_code}")

    # --- 8. Chat ---
    r = requests.post(f"{BASE_URL}/api/chat-messages",
                      json={"inputs": {}, "query": "你好",
                            "response_mode": "blocking", "user": "s9_test"},
                      timeout=60)
    ok = r.status_code == 200
    detail = f"status={r.status_code}"
    if ok:
        try:
            data = r.json()
            has_answer = "answer" in data
            detail += f", answer={'OK' if has_answer else 'MISSING'}"
            ok = ok and has_answer
        except Exception:
            if "event:" in r.text or "data:" in r.text:
                detail += ", SSE stream"
            else:
                ok = False
                detail += f", body={r.text[:80]}"
    else:
        detail += f", err={r.text[:100]}"
    record(8, "POST /api/chat-messages -> 200 + 有效响应", ok, detail)


# ============================================================================
# 二、Sprint 9 管理员功能 + 静态文件 (用例 17-20)
# 先执行，避免被安全测试耗尽限流/锁定配额
# ============================================================================

def test_sprint9_admin():
    hdr("二、Sprint 9 管理员功能 + 静态文件 (用例 17-20)")
    global ADMIN_TOKEN

    # --- 管理员登录 ---
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=5)
    if r.status_code == 200:
        ADMIN_TOKEN = r.json().get("token", "")
        print(f"  管理员登录 OK")
    else:
        print(f"  管理员登录 FAIL: status={r.status_code}, "
              f"msg={r.json().get('error','')[:50]}")
        ADMIN_TOKEN = None

    # --- 17. admin/stats ---
    if ADMIN_TOKEN:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        r = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers, timeout=10)
        ok = r.status_code == 200
        detail = f"status={r.status_code}"
        if ok:
            d = r.json()
            detail += (f", users={d.get('total_users')}, "
                      f"db={d.get('database_status')}, dify={d.get('dify_status')}")
        else:
            detail += f", body={r.text[:100]}"
        record(17, "GET /api/admin/stats(admin) -> 200", ok, detail)

        # 普通 token 访问 -> 403
        if TOKEN:
            r = requests.get(f"{BASE_URL}/api/admin/stats",
                           headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
            ok = r.status_code == 403
            record(17.1, "GET /api/admin/stats(普通用户) -> 403", ok,
                   f"status={r.status_code}")
        else:
            record(17.1, "GET /api/admin/stats(普通用户) -> 403", False, "无普通token")

        # --- 18. admin/users ---
        r = requests.get(f"{BASE_URL}/api/admin/users", headers=headers, timeout=10)
        ok = r.status_code == 200
        detail = f"status={r.status_code}"
        if ok:
            d = r.json()
            detail += f", total={d.get('total')}, page={d.get('page')}, " \
                      f"users_in_page={len(d.get('users',[]))}"
        else:
            detail += f", body={r.text[:100]}"
        record(18, "GET /api/admin/users(admin) -> 200", ok, detail)

        if TOKEN:
            r = requests.get(f"{BASE_URL}/api/admin/users",
                           headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
            ok = r.status_code == 403
            record(18.1, "GET /api/admin/users(普通用户) -> 403", ok,
                   f"status={r.status_code}")
        else:
            record(18.1, "GET /api/admin/users(普通用户) -> 403", False, "无普通token")
    else:
        record(17, "GET /api/admin/stats", False, "管理员登录失败")
        record(18, "GET /api/admin/users", False, "管理员登录失败")

    # --- 19. admin/health (无需 token) ---
    r = requests.get(f"{BASE_URL}/api/admin/health", timeout=10)
    ok = r.status_code == 200
    detail = f"status={r.status_code}"
    if ok:
        d = r.json()
        ok = ok and d.get("status") in ("ok", "degraded") and d.get("version") == "3.0.0"
        detail += f", svc={d.get('status')}, db={d.get('database')}, dify={d.get('dify')}"
    else:
        detail += f", body={r.text[:100]}"
    record(19, "GET /api/admin/health -> 200 + version=3.0.0", ok, detail)

    # --- 20. 前端静态文件 ---
    r = requests.get(f"{BASE_URL}/", timeout=5, headers={"Accept": "text/html"})
    ct = r.headers.get("content-type", "")
    is_html = "text/html" in ct
    is_not_json = "application/json" not in ct
    has_doctype = "<!DOCTYPE html>" in r.text[:200] or "<html" in r.text[:200]
    ok = r.status_code == 200 and is_html and is_not_json and has_doctype
    record(20, "GET / -> index.html(非JSON)", ok,
           f"status={r.status_code}, ct={ct}, len={len(r.text)}, html={'OK' if has_doctype else 'NO'}")


# ============================================================================
# 三、Sprint 8 数据功能回归 (用例 13-16)
# ============================================================================

def test_data_integrity():
    hdr("三、Sprint 8 数据功能回归 (用例 13-16)")

    # --- 13. 章节数量 ---
    expected = {"西游记": 100, "三国演义": 120, "红楼梦": 114, "水浒传": 111}
    all_match = True
    total = 0
    for book, exp_cnt in expected.items():
        r = requests.get(f"{BASE_URL}/api/chapters", params={"book": book}, timeout=10)
        if r.status_code == 200:
            cnt = len(r.json().get("chapters", []))
            total += cnt
            match = cnt == exp_cnt
            if not match:
                all_match = False
            print(f"  {book}: {cnt}/{exp_cnt} {'OK' if match else 'MISS'}")
        else:
            all_match = False
            print(f"  {book}: HTTP {r.status_code} MISS")
    record(13, f"章节数量: {total}/445 (西100/三120/红114/水111)", all_match and total == 445,
           f"total={total}" if total != 445 else "")

    # --- 14. 搜索 ---
    # 搜索已知词
    r = requests.get(f"{BASE_URL}/api/chapters/search",
                     params={"q": "大闹天宫"}, timeout=10)
    results = r.json().get("results", [])
    ok = r.status_code == 200 and len(results) > 0
    record(14, "搜索: 大闹天宫 -> 有结果", ok,
           f"status={r.status_code}, count={len(results)}")

    # 限定书名搜索
    r = requests.get(f"{BASE_URL}/api/chapters/search",
                     params={"book": "西游记", "q": "孙悟空"}, timeout=10)
    results = r.json().get("results", [])
    all_xiyou = all(item.get("book") == "西游记" for item in results)
    record(14.1, "搜索: 限定西游记+孙悟空 -> 仅西游记", all_xiyou or len(results) == 0,
           f"count={len(results)}, all_xiyou={all_xiyou}")

    # 空搜索词 -> 400
    r = requests.get(f"{BASE_URL}/api/chapters/search", params={"q": ""}, timeout=10)
    ok = r.status_code == 400
    record(14.2, "搜索: 空关键词 -> 400", ok, f"status={r.status_code}")

    # 不存在词的搜索：NATURAL LANGUAGE MODE 下 ngram 分词可能产生误匹配
    r = requests.get(f"{BASE_URL}/api/chapters/search",
                     params={"q": "量子计算机人工智能"}, timeout=10)
    results = r.json().get("results", [])
    # 即使返回结果，相关度应极低或结果应几乎无匹配
    ok = r.status_code == 200
    if results:
        # 检查结果是否真的与关键词相关（标题中应无匹配）
        has_title_match = any("量子" in item.get("title", "") or
                             "计算机" in item.get("title", "")
                             for item in results)
        detail = f"count={len(results)}, title_match={has_title_match}"
        ok = ok and not has_title_match  # 标题不应包含关键词
    else:
        detail = f"count=0 (空结果, 理想情况)"
    record(14.3, "搜索: 不存在词 -> 200 + 无相关标题匹配", ok, detail)

    # --- 15/16. 阅读历史 ---
    if TOKEN:
        headers = {"Authorization": f"Bearer {TOKEN}"}

        # 保存进度
        r = requests.post(f"{BASE_URL}/api/reading/progress",
                         json={"book": "西游记", "chapter_no": 7, "progress": 0.5},
                         headers=headers, timeout=10)
        ok = r.status_code == 200 and r.json().get("ok") is True
        record(15, "POST /api/reading/progress -> 200 + ok", ok,
               f"status={r.status_code}")

        # 获取最后阅读位置
        r = requests.get(f"{BASE_URL}/api/reading/last", headers=headers, timeout=10)
        last = r.json().get("last_read")
        ok = r.status_code == 200 and last is not None
        record(16, "GET /api/reading/last -> 200 + 有记录", ok,
               f"status={r.status_code}, last_read={'OK' if last else 'None'}")
    else:
        record(15, "POST /api/reading/progress", False, "无token")
        record(16, "GET /api/reading/last", False, "无token")


# ============================================================================
# 四、Sprint 7 安全功能回归 + 注入/XSS (用例 9-12, 21-22)
# 必须最后执行：限流和锁定会耗尽配额
# ============================================================================

def test_security():
    hdr("四、Sprint 7 安全功能回归 + 注入测试 (用例 9-12, 21-22)")

    # --- 9. 安全响应头 ---
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    headers_ok = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }
    all_ok = True
    for h, expected in headers_ok.items():
        actual = r.headers.get(h, "")
        ok = expected in actual
        if not ok:
            all_ok = False
        print(f"  {h}: {'OK' if ok else 'MISSING'} ({actual or '缺失'})")
    record(9, "安全响应头(Content-Type/Frame/XSS)", all_ok,
           "全部存在" if all_ok else "部分缺失")

    # --- 22. XSS 注册 (在限流测试之前执行) ---
    xss_email = f"{TEST_EMAIL_BASE}_xss@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": xss_email, "password": "Test123456",
                            "display_name": "<script>alert(1)</script>"}, timeout=5)
    ok = r.status_code in (200, 201, 422)
    record(22, "XSS: script标签注册 -> 201或422", ok,
           f"status={r.status_code}" +
           (f", body={r.json().get('error','')[:50]}" if not ok else ""))

    # --- 10. 限流: register ---
    rl_count = 0
    for i in range(8):
        email = f"{TEST_EMAIL_BASE}_rl{i}@test.com"
        r = requests.post(f"{BASE_URL}/api/auth/register",
                         json={"email": email, "password": "Test123456"}, timeout=5)
        if r.status_code == 429:
            rl_count += 1
            print(f"  请求 {i+1}/8: 429")
    ok = rl_count >= 1
    record(10, "限流: register 8次 -> 429", ok,
           f"429_count={rl_count}")

    # --- 11. 登录锁定 ---
    lock_email = f"{TEST_EMAIL_BASE}_lock@test.com"
    requests.post(f"{BASE_URL}/api/auth/register",
                  json={"email": lock_email, "password": "CorrectPass1"}, timeout=5)
    for i in range(5):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"email": lock_email, "password": "WrongPass1"}, timeout=5)
        print(f"  失败 {i+1}/5: status={r.status_code}")
    r6 = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": lock_email, "password": "WrongPass1"}, timeout=5)
    body6 = r6.json()
    locked = r6.status_code == 429 and ("分" in body6.get("error", "") or
                                         "过于频繁" in body6.get("error", ""))
    record(11, "登录锁定: 5次错->第6次429", locked,
           f"status={r6.status_code}, msg={body6.get('error','')[:60]}")

    # --- 12. 异常处理 ---
    # 404
    r = requests.get(f"{BASE_URL}/api/nonexistent_xyz", timeout=5)
    ok = r.status_code == 404
    try:
        ok = ok and "接口不存在" in r.json().get("error", "")
    except Exception:
        ok = False
    record(12, "异常处理: 404 -> JSON+中文提示", ok, f"status={r.status_code}")

    # 405
    r = requests.post(f"{BASE_URL}/api/health", timeout=5)
    ok = r.status_code == 405
    try:
        ok = ok and "请求方法不允许" in r.json().get("error", "")
    except Exception:
        ok = False
    record(12.1, "异常处理: 405 -> JSON+中文提示", ok, f"status={r.status_code}")

    # 422
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": f"{TEST_EMAIL_BASE}_422b@test.com"}, timeout=5)
    ok = r.status_code == 422
    try:
        body = r.json()
        ok = ok and ("校验" in body.get("error", "") or
                      "校验" in str(body.get("detail", "")))
    except Exception:
        ok = False
    record(12.2, "异常处理: 422 -> JSON+校验详情", ok, f"status={r.status_code}")

    # --- 21. SQL 注入 ---
    r = requests.get(f"{BASE_URL}/api/chapters",
                     params={"book": "西游记' OR '1'='1"}, timeout=5)
    ok = r.status_code not in (500, 503)
    record(21, "SQL注入: 章节查询 -> 非500/503", ok, f"status={r.status_code}")


# ============================================================================
# 主流程
# ============================================================================

def main():
    print("=" * 60)
    print("  测试 - Sprint 9 全量回归测试 S9-10")
    print(f"  目标: {BASE_URL}")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("  覆盖: Sprint 6/7/8/9 累计功能")
    print("=" * 60)

    # 前置检查
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code != 200:
            print(f"\n[FATAL] 服务不可用, status={r.status_code}")
            sys.exit(1)
        d = r.json()
        print(f"\n健康检查: version={d.get('version')}, db={d.get('database')}")
    except requests.ConnectionError:
        print(f"\n[FATAL] 无法连接 {BASE_URL}")
        sys.exit(1)

    # --- 执行顺序: 核心API -> 管理员 -> 数据完整性 -> 安全测试(最后) ---
    test_core_api()           # 1-8:   核心API
    test_sprint9_admin()      # 17-20: 管理员 + 静态文件 (在安全测试前)
    test_data_integrity()     # 13-16: 数据完整性
    test_security()           # 9-12, 21-22: 安全功能 + 注入 (最后)

    # --- 汇总 ---
    total = PASS + FAIL
    rate = (PASS / total * 100) if total > 0 else 0
    print("\n" + "=" * 60)
    print(f"  测试汇总: {PASS}/{total} 通过 ({rate:.1f}%)")
    print(f"  失败: {FAIL}")
    print("=" * 60)
    for r in results:
        print(r)

    # --- 版本质量判定 ---
    print("\n" + "=" * 60)
    print("  版本质量判定:")
    print(f"    通过率: {rate:.1f}% ({PASS}/{total})")

    # 识别关键失败项
    critical_fails = [r for r in results if r.startswith("[FAIL]") and
                      ("17" in r or "18" in r or "1" in r.split("#")[1].split()[0])]

    if rate >= 95 and FAIL == 0:
        verdict = "PASS - 准予发布 V3.0.0"
    elif rate >= 90:
        verdict = "CONDITIONAL PASS - 存在非关键问题，建议修复后发布"
    else:
        verdict = "REJECT - 未通过验收，禁止上线"

    print(f"    判定: {verdict}")
    if FAIL > 0:
        print(f"  失败项明细 ({FAIL}):")
        for r in results:
            if r.startswith("[FAIL]"):
                # 提取测试编号
                parts = r.split("#")
                test_id = parts[1].split()[0] if len(parts) > 1 else "?"
                print(f"    #{test_id}: {r.split(chr(10))[0][7:] if chr(10) in r else r[7:]}")
    print("=" * 60)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
