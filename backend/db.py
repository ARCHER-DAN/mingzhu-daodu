"""数据库连接管理"""
import pymysql
from backend.config import env


def get_conn():
    return pymysql.connect(
        host=env('MYSQL_HOST'),
        port=int(env('MYSQL_PORT', '3306')),
        user=env('MYSQL_USER'),
        password=env('MYSQL_PASSWORD'),
        database=env('MYSQL_DATABASE'),
        charset='utf8mb4',
        autocommit=True,
    )


def init_db():
    """创建数据库和用户表"""
    conn = pymysql.connect(
        host=env('MYSQL_HOST'),
        port=int(env('MYSQL_PORT', '3306')),
        user=env('MYSQL_USER'),
        password=env('MYSQL_PASSWORD'),
        charset='utf8mb4',
    )
    with conn.cursor() as cur:
        cur.execute(
            'CREATE DATABASE IF NOT EXISTS {} '
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'.format(env('MYSQL_DATABASE'))
        )
    conn.close()

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100),
                is_admin TINYINT DEFAULT 0,
                own_api_key VARCHAR(255) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expire_at TIMESTAMP NULL DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
    conn.close()


def add_expire_column():
    """迁移：为已有 users 表添加 expire_at 列"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM users LIKE 'expire_at'")
        if not cur.fetchone():
            cur.execute(
                'ALTER TABLE users ADD COLUMN expire_at TIMESTAMP NULL DEFAULT NULL'
            )
    conn.close()
