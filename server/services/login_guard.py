"""
登录失败限流 — IP 级别失败计数 + 临时锁定
与 slowapi 频率限流互补：slowapi 管请求频率，此模块管失败次数锁定。

规则：
- 同一 IP 连续 5 次登录失败后，锁定 15 分钟
- 登录成功后清除该 IP 的失败计数
- 过期锁自动清理

线程安全：使用 threading.Lock 保护共享字典。
"""
import time
from threading import Lock

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
MAX_FAILURES = 5              # 最大失败次数
LOCK_DURATION = 15 * 60       # 锁定时长（秒）

# ---------------------------------------------------------------------------
# 内存存储
# ---------------------------------------------------------------------------
_failures: dict[str, dict] = {}
_lock = Lock()


def _cleanup_expired() -> None:
    """清理所有过期记录"""
    now = time.time()
    expired = [
        ip for ip, rec in _failures.items()
        if rec.get("locked_until", 0) <= now
    ]
    for ip in expired:
        del _failures[ip]


def check_login_allowed(ip: str) -> bool:
    """检查指定 IP 是否允许登录

    Returns:
        True — 允许登录
        False — 仍在锁定期内
    """
    with _lock:
        record = _failures.get(ip)
        if not record:
            return True

        locked_until = record.get("locked_until", 0)
        if locked_until > time.time():
            return False

        # 锁已过期（locked_until > 0 且已过有效期），清理记录
        # 注意：locked_until == 0 表示尚未达到锁定阈值，不应删除记录
        if locked_until > 0:
            del _failures[ip]
        return True


def record_login_failure(ip: str) -> None:
    """记录一次登录失败，达到阈值时锁定"""
    with _lock:
        record = _failures.get(ip)
        if not record:
            record = {"failures": 0, "locked_until": 0}

        record["failures"] += 1
        if record["failures"] >= MAX_FAILURES:
            record["locked_until"] = time.time() + LOCK_DURATION

        _failures[ip] = record


def record_login_success(ip: str) -> None:
    """登录成功后清除该 IP 的失败记录"""
    with _lock:
        _failures.pop(ip, None)


def get_lock_remaining_seconds(ip: str) -> int:
    """获取指定 IP 剩余锁定秒数（0 = 未锁定）"""
    record = _failures.get(ip)
    if not record:
        return 0
    remaining = record.get("locked_until", 0) - time.time()
    return max(0, int(remaining))
