"""测试 - Sprint 8 数据完整性测试 S8-08
==========================================
验证脚本导入 MySQL chapters 表的 445 章数据完整性。
测试依赖：uvicorn server.main:app --port 8080 已启动
"""

import requests
import json
import os
import sys
import re

BASE = 'http://localhost:8080'
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# 用于认证测试的临时用户
TEST_EMAIL = None
TEST_PASSWORD = 'Test123456'
TOKEN = None

results = {
    'total': 0,
    'pass': 0,
    'fail': 0,
    'failures': [],
}


def record(name, condition, detail=''):
    results['total'] += 1
    if condition:
        results['pass'] += 1
        print(f'  PASS  {name}')
    else:
        results['fail'] += 1
        results['failures'].append({'name': name, 'detail': detail})
        print(f'  FAIL  {name}  -- {detail}')


# ============================================================================
# 工具函数
# ============================================================================

def read_txt_head(book, chapter_no):
    """读取 txt 文件的前500字作为对比基准"""
    dir_path = os.path.join(DATA_DIR, book, '01_原著原文')
    if not os.path.isdir(dir_path):
        return None
    pattern = re.compile(rf'^第{chapter_no:03d}回_.*\.txt$')
    for fname in os.listdir(dir_path):
        if pattern.match(fname):
            fpath = os.path.join(dir_path, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                return f.read()[:500]
    return None


def read_txt_full(book, chapter_no):
    """读取整个 txt 文件内容"""
    dir_path = os.path.join(DATA_DIR, book, '01_原著原文')
    if not os.path.isdir(dir_path):
        return ''
    pattern = re.compile(rf'^第{chapter_no:03d}回_.*\.txt$')
    for fname in os.listdir(dir_path):
        if pattern.match(fname):
            fpath = os.path.join(dir_path, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                return f.read()
    return ''


def clean_text(text):
    """清理比较文本：去掉多余空白行、统一空白"""
    return re.sub(r'\s+', '', text)


# ============================================================================
# === 一、数量校验 ===
# ============================================================================

def test_01_chapter_counts():
    print('\n' + '=' * 60)
    print('一、数量校验')
    print('=' * 60)

    expected = {
        '西游记': 100,
        '三国演义': 120,
        '红楼梦': 114,
        '水浒传': 111,
    }
    total_count = 0

    for book_name, expected_count in expected.items():
        r = requests.get(f'{BASE}/api/chapters', params={'book': book_name}, timeout=10)
        print(f'  GET /api/chapters?book={book_name}  ->  status={r.status_code}')
        if r.status_code != 200:
            record(f'数量-{book_name}(HTTP 200)', False, f'status={r.status_code}, body={r.text[:100]}')
            continue
        data = r.json()
        chapters = data.get('chapters', [])
        actual = len(chapters)
        total_count += actual
        match = actual == expected_count
        record(f'数量-{book_name} 应{expected_count}回 实{actual}回', match,
               f'差额={actual - expected_count}' if not match else '')

    record(f'数量-总计应445回 实{total_count}回', total_count == 445,
           f'差额={total_count - 445}' if total_count != 445 else '')


# ============================================================================
# === 二、内容抽样校验 ===
# ============================================================================

SAMPLE_CHAPTERS = [
    ('西游记', [1, 50, 100]),
    ('三国演义', [1, 60, 120]),
    ('红楼梦', [1, 57, 114]),
    ('水浒传', [1, 55, 111]),
]


def test_02_content_sampling():
    print('\n' + '=' * 60)
    print('二、内容抽样校验')
    print('=' * 60)

    for book, chapters in SAMPLE_CHAPTERS:
        print(f'\n  --- {book} ---')
        for ch_no in chapters:
            prefix = f'{book}-第{ch_no}回'

            # API 请求
            r = requests.get(f'{BASE}/api/chapters', params={'book': book, 'chapter': ch_no}, timeout=10)
            if r.status_code != 200:
                record(f'{prefix}-HTTP 200', False, f'status={r.status_code}')
                continue
            data = r.json()

            # 验证 title 非空
            title = data.get('title', '')
            record(f'{prefix}-标题非空', bool(title and title.strip()),
                   '标题为空' if not title else '')

            # 验证 content 非空
            content = data.get('content', '')
            record(f'{prefix}-正文非空', bool(content and content.strip()),
                   '正文为空' if not content else '')

            # 验证 content 长度 > 500
            content_len = len(content)
            record(f'{prefix}-正文长度>{500}(实{content_len})', content_len > 500,
                   f'长度={content_len}' if content_len <= 500 else '')

            # 离线文件一致性对比：API 返回的 content 开头与 txt 一致
            txt_head = read_txt_head(book, ch_no)
            if txt_head:
                api_head_clean = clean_text(content[:500])
                txt_head_clean = clean_text(txt_head[:500])
                match = (api_head_clean == txt_head_clean)
                record(f'{prefix}-正文开头与txt一致', match,
                       f'API开头: {content[:80]!r} | txt开头: {txt_head[:80]!r}' if not match else '')
            else:
                record(f'{prefix}-txt文件存在', False, '找不到对应的txt源文件')


# ============================================================================
# === 三、搜索功能验证 ===
# ============================================================================

def test_03_search():
    print('\n' + '=' * 60)
    print('三、搜索功能验证')
    print('=' * 60)

    # 3.1 跨书搜索"大闹天宫"
    r = requests.get(f'{BASE}/api/chapters/search', params={'q': '大闹天宫'}, timeout=10)
    print(f'  搜索"大闹天宫" -> status={r.status_code}')
    record('搜索-大闹天宫(HTTP 200)', r.status_code == 200,
           f'status={r.status_code}, body={r.text[:100]}' if r.status_code != 200 else '')
    if r.status_code == 200:
        data = r.json()
        results_list = data.get('results', [])
        record('搜索-大闹天宫(有结果)', len(results_list) > 0,
               '返回空数组' if len(results_list) == 0 else '')
        print(f'    返回 {len(results_list)} 条结果')
        if results_list:
            print(f'    第1条: {results_list[0]}')

    # 3.2 限定书名搜索"孙悟空"
    r = requests.get(f'{BASE}/api/chapters/search',
                     params={'book': '西游记', 'q': '孙悟空'}, timeout=10)
    print(f'  搜索 book=西游记&q=孙悟空 -> status={r.status_code}')
    record('搜索-限定西游记+孙悟空(HTTP 200)', r.status_code == 200,
           f'status={r.status_code}' if r.status_code != 200 else '')
    if r.status_code == 200:
        data = r.json()
        results_list = data.get('results', [])
        record('搜索-限定西游记+孙悟空(有结果)', len(results_list) > 0,
               '返回空数组' if len(results_list) == 0 else '')
        # 验证所有结果都是西游记
        all_xiyou = all(item.get('book') == '西游记' for item in results_list)
        record('搜索-限定西游记+孙悟空(仅西游记)', all_xiyou or len(results_list) == 0,
               '返回了其他书的结果' if not all_xiyou else '')
        print(f'    返回 {len(results_list)} 条结果')

    # 3.3 搜索不存在的词
    r = requests.get(f'{BASE}/api/chapters/search', params={'q': 'xyzabc123'}, timeout=10)
    print(f'  搜索"xyzabc123" -> status={r.status_code}')
    record('搜索-不存在词(HTTP 200)', r.status_code == 200,
           f'status={r.status_code}' if r.status_code != 200 else '')
    if r.status_code == 200:
        data = r.json()
        results_list = data.get('results', [])
        record('搜索-不存在词(返回空数组)', len(results_list) == 0,
               f'返回了{len(results_list)}条结果' if len(results_list) > 0 else '')
        record('搜索-不存在词(非404)', r.status_code != 404,
               f'返回到404' if r.status_code == 404 else '')


# ============================================================================
# === 四、新增 API 验证 ===
# ============================================================================

def test_04_new_apis():
    print('\n' + '=' * 60)
    print('四、新增 API 验证')
    print('=' * 60)

    # 4.1 GET /api/chapters/books
    r = requests.get(f'{BASE}/api/chapters/books', timeout=10)
    print(f'  GET /api/chapters/books -> status={r.status_code}')
    record('books列表(HTTP 200)', r.status_code == 200,
           f'status={r.status_code}' if r.status_code != 200 else '')
    if r.status_code == 200:
        data = r.json()
        books = data.get('books', [])
        record('books列表(返回4本)', len(books) == 4,
               f'实际返回{len(books)}本: {books}' if len(books) != 4 else '')
        expected_books = {'西游记', '三国演义', '红楼梦', '水浒传'}
        record('books列表(书名正确)', set(books) == expected_books,
               f'差异: {set(books) ^ expected_books}' if set(books) != expected_books else '')

    # 4.2-4.4 需要认证的 API
    # 注册临时用户获取 token
    global TEST_EMAIL, TOKEN
    import time
    TEST_EMAIL = f's8test_{int(time.time())}@example.com'

    r = requests.post(f'{BASE}/api/auth/register',
                      json={'email': TEST_EMAIL, 'password': TEST_PASSWORD,
                            'display_name': 'S8测试员'}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get('token', '')
        print(f'  注册测试用户成功: {TEST_EMAIL}')
    else:
        # 可能用户已存在，尝试登录
        r = requests.post(f'{BASE}/api/auth/login',
                          json={'email': TEST_EMAIL, 'password': TEST_PASSWORD}, timeout=10)
        if r.status_code == 200:
            TOKEN = r.json().get('token', '')
            print(f'  登录测试用户成功: {TEST_EMAIL}')
        else:
            TOKEN = None
            print(f'  认证失败，注册返回 {r.status_code}: {r.text[:100]}')

    if TOKEN:
        headers = {'Authorization': f'Bearer {TOKEN}'}

        # 4.2 GET /api/reading/progress
        r = requests.get(f'{BASE}/api/reading/progress',
                         params={'book': '西游记'}, headers=headers, timeout=10)
        print(f'  GET /api/reading/progress -> status={r.status_code}')
        record('reading/progress(HTTP 200)', r.status_code == 200,
               f'status={r.status_code}, body={r.text[:100]}' if r.status_code != 200 else '')

        # 4.3 POST /api/reading/progress
        r = requests.post(f'{BASE}/api/reading/progress',
                          json={'book': '西游记', 'chapter_no': 7, 'progress': 0.5},
                          headers=headers, timeout=10)
        print(f'  POST /api/reading/progress -> status={r.status_code}')
        record('reading/progress POST(HTTP 200)', r.status_code == 200,
               f'status={r.status_code}, body={r.text[:100]}' if r.status_code != 200 else '')
        if r.status_code == 200:
            record('reading/progress POST(ok=True)', r.json().get('ok') is True,
                   f'ok={r.json().get("ok")}' if r.json().get('ok') is not True else '')

        # 4.4 GET /api/reading/last
        r = requests.get(f'{BASE}/api/reading/last', headers=headers, timeout=10)
        print(f'  GET /api/reading/last -> status={r.status_code}')
        record('reading/last(HTTP 200)', r.status_code == 200,
               f'status={r.status_code}, body={r.text[:100]}' if r.status_code != 200 else '')
        if r.status_code == 200:
            data = r.json()
            last_read = data.get('last_read')
            record('reading/last(有最近记录)', last_read is not None,
                   'last_read为None（预期：刚保存进度后应有记录）' if last_read is None else '')
    else:
        record('认证-获取token失败', False, '无法注册或登录测试用户，跳过后三项测试')
        print('  跳过阅读历史API测试（无法获取token）')


# ============================================================================
# === 五、边界情况 ===
# ============================================================================

def test_05_boundary():
    print('\n' + '=' * 60)
    print('五、边界情况')
    print('=' * 60)

    # 5.1 不存在的书
    r = requests.get(f'{BASE}/api/chapters', params={'book': '金瓶梅'}, timeout=10)
    print(f'  /api/chapters?book=金瓶梅 -> status={r.status_code}')
    record('边界-不存在的书(404)', r.status_code == 404,
           f'status={r.status_code}（预期404）' if r.status_code != 404 else '')

    # 5.2 超出范围的回号
    r = requests.get(f'{BASE}/api/chapters',
                     params={'book': '西游记', 'chapter': 999}, timeout=10)
    print(f'  /api/chapters?book=西游记&chapter=999 -> status={r.status_code}')
    record('边界-超范围回号(404)', r.status_code == 404,
           f'status={r.status_code}（预期404）' if r.status_code != 404 else '')

    # 5.3 空搜索词
    r = requests.get(f'{BASE}/api/chapters/search', params={'q': ''}, timeout=10)
    print(f'  /api/chapters/search?q= -> status={r.status_code}')
    record('边界-空搜索词(400/422)', r.status_code in (400, 422),
           f'status={r.status_code}（预期400或422）' if r.status_code not in (400, 422) else '')


# ============================================================================
# 主流程
# ============================================================================

def main():
    print('=' * 60)
    print('测试 - Sprint 8 数据完整性测试 S8-08')
    print(f'目标: {BASE}')
    print('=' * 60)

    # 前置检查：服务可用性
    try:
        r = requests.get(f'{BASE}/api/chapters/books', timeout=5)
        print(f'\n服务连通检查: status={r.status_code}')
        if r.status_code >= 500:
            print('服务异常 (5xx)，终止测试')
            sys.exit(1)
    except requests.ConnectionError:
        print(f'\n无法连接服务 {BASE}，请确认 FastAPI 服务已启动：')
        print('  uvicorn server.main:app --host 0.0.0.0 --port 8080')
        sys.exit(1)

    test_01_chapter_counts()
    test_02_content_sampling()
    test_03_search()
    test_04_new_apis()
    test_05_boundary()

    # === 汇总 ===
    print('\n' + '=' * 60)
    print('测试汇总')
    print('=' * 60)
    total = results['total']
    passed = results['pass']
    failed = results['fail']
    pass_rate = passed / total * 100 if total > 0 else 0
    print(f'  总计: {total} 项')
    print(f'  通过: {passed} 项')
    print(f'  失败: {failed} 项')
    print(f'  通过率: {pass_rate:.1f}%')

    if results['failures']:
        print(f'\n失败明细:')
        for f in results['failures']:
            print(f'  [{f["name"]}] {f["detail"]}')

    # 离线数据源问题标注
    print('\n离线数据源预检发现（非API测试项）：')
    print('  1. 红楼梦-文件拆分：57/58, 63/64, 65/66, 77/78, 81/82, 83/84 使用了1/2后缀')
    print('     - 第058回文件名内容标题为"第五十七回"（实际是57回下半部分）')
    print('     - 第064回文件名内容标题为"第六十三回"')
    print('     - 这会导致数据库中的标题可能重复（同标题不同内容）')
    print('  2. 红楼梦-第114回：文件名114回，但内容标题为"第一一九回"')
    print('  3. 水浒传-第111回：文件名111回，但内容标题为"第一百二十回"')

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
