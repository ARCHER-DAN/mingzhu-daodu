"""
S8-02: 将 data/<名著>/01_原著原文/*.txt 导入 MySQL chapters 表
==============================================================

功能：
  - 扫描 data 目录下四大名著的 txt 文件
  - 解析文件名提取 chapter_no + title
  - 使用 INSERT ... ON DUPLICATE KEY UPDATE 幂等导入
  - 批量提交（每 10 章一次 commit）
  - 支持 --dry-run（预览不写入）和 --book（只导指定书）

用法：
  python scripts/import_chapters.py                  # 导入全部
  python scripts/import_chapters.py --dry-run         # 预览
  python scripts/import_chapters.py --book 西游记      # 只导西游记
"""

import argparse
import os
import re
import sys

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_conn

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# 文件名正则：第001回_标题名.txt
FILENAME_RE = re.compile(r'^第(\d+)回_(.+)\.txt$')

# 每 10 章 commit 一次
BATCH_SIZE = 10


def parse_filename(filename: str) -> tuple[int, str] | None:
    """从文件名提取 (chapter_no, title)，解析失败返回 None。

    Example:
        >>> parse_filename('第001回_灵根育孕源流出 心性修持大道生.txt')
        (1, '灵根育孕源流出 心性修持大道生')
    """
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    chapter_no = int(m.group(1))
    title = m.group(2)
    return chapter_no, title


def read_file_utf8(filepath: str) -> str | None:
    """以 UTF-8 读取文件内容，失败返回 None。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (UnicodeDecodeError, OSError) as e:
        print(f'[WARNING] 文件编码错误或无法读取: {filepath} — {e}')
        return None


def get_books() -> list[str]:
    """扫描 data 目录，返回所有有 01_原著原文 子目录的书名。"""
    books = []
    if not os.path.isdir(DATA_DIR):
        print(f'[ERROR] data 目录不存在: {DATA_DIR}')
        return books

    for entry in os.listdir(DATA_DIR):
        book_dir = os.path.join(DATA_DIR, entry)
        chapters_dir = os.path.join(book_dir, '01_原著原文')
        if os.path.isdir(chapters_dir):
            books.append(entry)
    return sorted(books)


def scan_book(book: str) -> list[dict]:
    """扫描一本书的所有章节文件，返回待导入项列表。

    Returns:
        [{'book': '西游记', 'chapter_no': 1, 'title': '...', 'content': '...', 'filepath': '...'}, ...]
    遇到异常文件打印 warning 并跳过。
    """
    chapters_dir = os.path.join(DATA_DIR, book, '01_原著原文')
    items = []

    if not os.path.isdir(chapters_dir):
        print(f'[WARNING] {book} 缺少 01_原著原文 目录，跳过')
        return items

    for filename in sorted(os.listdir(chapters_dir)):
        if not filename.endswith('.txt'):
            continue

        full_path = os.path.join(chapters_dir, filename)
        parsed = parse_filename(filename)
        if parsed is None:
            print(f'[WARNING] 文件名格式异常，跳过: {full_path}')
            continue

        chapter_no, title = parsed

        # 检查空文件
        try:
            file_size = os.path.getsize(full_path)
        except OSError:
            file_size = 0
        if file_size == 0:
            print(f'[WARNING] 空文件，跳过: {full_path}')
            continue

        content = read_file_utf8(full_path)
        if content is None:
            continue

        items.append({
            'book': book,
            'chapter_no': chapter_no,
            'title': title,
            'content': content,
            'filepath': full_path,
        })

    return items


def import_book(conn, book: str, dry_run: bool = False) -> dict:
    """导入一本书的全部章节。

    Args:
        conn: pymysql 连接（autocommit=False 模式）
        book: 书名
        dry_run: True 时只打印不写入

    Returns:
        {'success': N, 'skip': N, 'fail': N}
    """
    items = scan_book(book)
    stats = {'success': 0, 'skip': 0, 'fail': 0}

    if not items:
        return stats

    print(f'\n===== {book}: 共 {len(items)} 章 =====')

    cur = conn.cursor()

    for i, item in enumerate(items):
        if dry_run:
            print(f'[DRY-RUN] {item["book"]} 第{item["chapter_no"]}回 {item["title"]} '
                  f'({len(item["content"])} 字)')
            stats['success'] += 1
            continue

        try:
            cur.execute(
                'INSERT INTO chapters (book, chapter_no, title, content) '
                'VALUES (%s, %s, %s, %s) '
                'ON DUPLICATE KEY UPDATE title = VALUES(title), content = VALUES(content)',
                (item['book'], item['chapter_no'], item['title'], item['content']),
            )
            print(f'[OK] {item["book"]} 第{item["chapter_no"]}回 {item["title"]}')
            stats['success'] += 1
        except Exception as e:
            print(f'[FAIL] {item["book"]} 第{item["chapter_no"]}回: {e}')
            stats['fail'] += 1

        # 批量提交
        if not dry_run and (i + 1) % BATCH_SIZE == 0:
            conn.commit()

    # 提交剩余
    if not dry_run:
        conn.commit()

    print(f'{book}: {stats["success"]} 章导入成功')
    if stats['skip']:
        print(f'{book}: {stats["skip"]} 章跳过')
    if stats['fail']:
        print(f'{book}: {stats["fail"]} 章失败')

    return stats


def main():
    parser = argparse.ArgumentParser(description='导入名著章节到 MySQL chapters 表')
    parser.add_argument('--dry-run', action='store_true', help='只扫描预览，不实际写入数据库')
    parser.add_argument('--book', type=str, default=None, help='指定书名（如：西游记），不指定则导入全部')
    args = parser.parse_args()

    # 确定要导入的书籍
    all_books = get_books()
    if not all_books:
        print('[ERROR] 未找到任何书籍数据目录')
        sys.exit(1)

    if args.book:
        if args.book not in all_books:
            print(f'[ERROR] 未找到书籍: {args.book}，可用的有: {all_books}')
            sys.exit(1)
        books = [args.book]
    else:
        books = all_books

    print(f'数据目录: {DATA_DIR}')
    print(f'待导入书籍: {books}')
    print(f'模式: {"预览" if args.dry_run else "实际写入"}')
    print(f'批量提交: 每 {BATCH_SIZE} 章')

    total = {'success': 0, 'skip': 0, 'fail': 0}

    if args.dry_run:
        for book in books:
            items = scan_book(book)
            for item in items:
                print(f'[DRY-RUN] {item["book"]} 第{item["chapter_no"]}回 {item["title"]} '
                      f'({len(item["content"])} 字)')
                total['success'] += 1
        total_files = total['success']
    else:
        conn = get_conn()
        conn.autocommit = False
        try:
            for book in books:
                stats = import_book(conn, book, dry_run=False)
                total['success'] += stats['success']
                total['skip'] += stats['skip']
                total['fail'] += stats['fail']
        finally:
            conn.close()

    # 汇总
    total_files = total['success'] + total['skip'] + total['fail']
    print(f'\n===== 导入汇总 =====')
    print(f'总文件数: {total_files}')
    print(f'成功: {total["success"]}')
    print(f'跳过: {total["skip"]}')
    print(f'失败: {total["fail"]}')

    if total['fail'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
