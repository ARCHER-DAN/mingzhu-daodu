"""用户认证：注册、登录、Token验证"""
import bcrypt
import jwt
import datetime
from backend.db import get_conn
from backend.config import env

JWT_SECRET = env('JWT_SECRET')
JWT_EXPIRE_HOURS = 72
TEST_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user: dict) -> str:
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'is_admin': bool(user['is_admin']),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None


def _cleanup_expired(cur):
    """删除所有已过期的非管理员用户"""
    cur.execute(
        'DELETE FROM users WHERE is_admin = 0 AND expire_at IS NOT NULL AND expire_at < NOW()'
    )


def register_user(email: str, password: str, display_name: str = None) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                return None
            pwd_hash = hash_password(password)
            cur.execute(
                'INSERT INTO users (email, password_hash, display_name, expire_at) '
                'VALUES (%s, %s, %s, NOW() + INTERVAL %s MINUTE)',
                (email, pwd_hash, display_name or email.split('@')[0], TEST_EXPIRE_MINUTES),
            )
            conn.commit()
            return {
                'id': cur.lastrowid,
                'email': email,
                'display_name': display_name or email.split('@')[0],
                'is_admin': 0,
            }
    finally:
        conn.close()


def login_user(email: str, password: str) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 先清理过期用户
            _cleanup_expired(cur)

            cur.execute(
                'SELECT id, email, password_hash, display_name, is_admin, own_api_key, expire_at '
                'FROM users WHERE email = %s',
                (email,),
            )
            row = cur.fetchone()
            if not row:
                return None
            if not verify_password(password, row[2]):
                return None

            # 检查是否过期（非管理员）
            if not row[4] and row[6] and row[6] < datetime.datetime.now():
                cur.execute('DELETE FROM users WHERE id = %s', (row[0],))
                conn.commit()
                return None

            return {
                'id': row[0],
                'email': row[1],
                'display_name': row[3],
                'is_admin': bool(row[4]),
                'own_api_key': row[5],
            }
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _cleanup_expired(cur)

            cur.execute(
                'SELECT id, email, display_name, is_admin, own_api_key, created_at, expire_at '
                'FROM users WHERE id = %s',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            # 非管理员检查过期
            if not row[3] and row[6] and row[6] < datetime.datetime.now():
                cur.execute('DELETE FROM users WHERE id = %s', (row[0],))
                conn.commit()
                return None

            return {
                'id': row[0],
                'email': row[1],
                'display_name': row[2],
                'is_admin': bool(row[3]),
                'own_api_key': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
            }
    finally:
        conn.close()
