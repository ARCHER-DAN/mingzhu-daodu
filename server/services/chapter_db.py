"""
章节数据访问层 + 阅读历史数据访问层
===========================================
S8-01: chapters 表 DDL + CRUD + 全文搜索
S8-05: reading_history 表 DDL + CRUD

所有 SQL 使用参数化查询防注入。
依赖 backend.db.get_conn() 获取数据库连接。
"""
import pymysql
from backend.db import get_conn


# ============================================================================
# S8-01: chapters 表
# ============================================================================

def init_chapters_table():
    """创建 chapters 表（如果不存在）。

    自动尝试创建 FULLTEXT 索引（ngram 分词），
    若 MySQL 版本过低则回退到默认分词器，均失败则跳过全文索引。
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    book VARCHAR(50) NOT NULL,
                    chapter_no INT NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    content LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_book_chapter (book, chapter_no)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        # FULLTEXT 索引单独创建：ngram 需要 MySQL 5.7.6+
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'ALTER TABLE chapters '
                    'ADD FULLTEXT INDEX ft_content (title, content) WITH PARSER ngram'
                )
        except pymysql.err.OperationalError:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'ALTER TABLE chapters '
                        'ADD FULLTEXT INDEX ft_content (title, content)'
                    )
            except pymysql.err.OperationalError:
                # MySQL < 5.6 InnoDB 不支持 FULLTEXT，静默跳过
                print('[chapter_db] 全文索引创建失败（MySQL 版本过低），搜索功能不可用')
    finally:
        conn.close()


def get_chapters_by_book(book: str) -> list[dict]:
    """查询某书的全部章节目录，按回号升序排列。

    Returns:
        [{'id': 1, 'title': '...', 'filename': '第001回_xxx.txt'}, ...]
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT chapter_no, title FROM chapters '
                'WHERE book = %s ORDER BY chapter_no',
                (book,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'filename': f'第{row[0]:03d}回_{row[1]}.txt',
                }
                for row in rows
            ]
    finally:
        conn.close()


def get_chapter(book: str, chapter_no: int) -> dict | None:
    """查询单章正文内容。

    Returns:
        {'id': 1, 'title': '...', 'content': '...'} 或 None
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT chapter_no, title, content FROM chapters '
                'WHERE book = %s AND chapter_no = %s',
                (book, chapter_no),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {'id': row[0], 'title': row[1], 'content': row[2]}
    finally:
        conn.close()


def search_chapters(book: str | None = None, keyword: str = '') -> list[dict]:
    """全文搜索章节内容。book 为 None 时全局搜索。

    使用 MySQL NATURAL LANGUAGE MODE 全文搜索，按相关度降序排列，最多返回 50 条。
    若 FULLTEXT 索引不可用则返回空列表（不抛异常）。

    Returns:
        [{'book': '西游记', 'id': 7, 'title': '...', 'relevance': 1.234}, ...]
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if book:
                cur.execute(
                    'SELECT book, chapter_no, title, '
                    'MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) AS relevance '
                    'FROM chapters '
                    'WHERE book = %s '
                    '  AND MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) '
                    'ORDER BY relevance DESC LIMIT 50',
                    (keyword, book, keyword),
                )
            else:
                cur.execute(
                    'SELECT book, chapter_no, title, '
                    'MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) AS relevance '
                    'FROM chapters '
                    'WHERE MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) '
                    'ORDER BY relevance DESC LIMIT 50',
                    (keyword, keyword),
                )
            rows = cur.fetchall()
            return [
                {
                    'book': row[0],
                    'id': row[1],
                    'title': row[2],
                    'relevance': round(float(row[3]), 4),
                }
                for row in rows
            ]
    except pymysql.err.OperationalError:
        # FULLTEXT 索引不存在或不可用，返回空结果
        return []
    finally:
        conn.close()


def get_all_books() -> list[str]:
    """查询数据库中所有已导入的书籍名（去重排序）。

    Returns:
        ['三国演义', '水浒传', '红楼梦', '西游记']
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT DISTINCT book FROM chapters ORDER BY book')
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


# ============================================================================
# S8-05: reading_history 表
# ============================================================================

def init_reading_history_table():
    """创建 reading_history 表（如果不存在）。

    外键引用 users(id)，用户删除时级联清除阅读记录。
    uk_user_book_chapter 唯一约束保证同一用户同一章只有一条进度记录。
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    book VARCHAR(50) NOT NULL,
                    chapter_no INT NOT NULL,
                    progress FLOAT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_book_chapter (user_id, book, chapter_no),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
    finally:
        conn.close()


def save_reading_progress(user_id: int, book: str, chapter_no: int, progress: float):
    """保存（插入或更新）用户阅读进度。

    使用 INSERT ... ON DUPLICATE KEY UPDATE 实现 upsert，
    重复(user_id, book, chapter_no)时更新 progress 和 updated_at。
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO reading_history (user_id, book, chapter_no, progress) '
                'VALUES (%s, %s, %s, %s) '
                'ON DUPLICATE KEY UPDATE progress = VALUES(progress)',
                (user_id, book, chapter_no, progress),
            )
            conn.commit()
    finally:
        conn.close()


def get_reading_progress(user_id: int, book: str) -> list[dict]:
    """获取用户某本书的全部章节阅读进度，按回号升序。

    Returns:
        [{'book': '西游记', 'chapter_no': 1, 'progress': 0.5, 'updated_at': '...'}, ...]
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT book, chapter_no, progress, updated_at '
                'FROM reading_history '
                'WHERE user_id = %s AND book = %s '
                'ORDER BY chapter_no',
                (user_id, book),
            )
            rows = cur.fetchall()
            return [
                {
                    'book': row[0],
                    'chapter_no': row[1],
                    'progress': row[2],
                    'updated_at': row[3].isoformat() if row[3] else None,
                }
                for row in rows
            ]
    finally:
        conn.close()


def get_last_read(user_id: int) -> dict | None:
    """获取用户最后阅读位置（按 updated_at 降序取第一条）。

    Returns:
        {'book': '西游记', 'chapter_no': 7, 'progress': 0.5, 'updated_at': '...'} 或 None
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT book, chapter_no, progress, updated_at '
                'FROM reading_history '
                'WHERE user_id = %s '
                'ORDER BY updated_at DESC LIMIT 1',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'book': row[0],
                'chapter_no': row[1],
                'progress': row[2],
                'updated_at': row[3].isoformat() if row[3] else None,
            }
    finally:
        conn.close()
