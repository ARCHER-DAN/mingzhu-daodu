"""初始化管理员账号"""
from backend.db import get_conn
from backend.auth import hash_password
from backend.config import env


def init_admin():
    email = env('ADMIN_EMAIL')
    password = env('ADMIN_PASSWORD')
    display_name = env('ADMIN_DISPLAY_NAME', '管理员')

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cur.fetchone():
            print('管理员账号已存在，跳过')
        else:
            pwd_hash = hash_password(password)
            cur.execute(
                'INSERT INTO users (email, password_hash, display_name, is_admin) '
                'VALUES (%s, %s, %s, 1)',
                (email, pwd_hash, display_name),
            )
            conn.commit()
            print(f'管理员账号已创建: {email}')
    conn.close()


if __name__ == '__main__':
    from backend.db import init_db
    init_db()
    init_admin()
