import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import './AdminPanel.css'

function formatTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return '—'
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch { return '—' }
}

function Spinner() {
  return (
    <div className="admin-spinner-wrap">
      <div className="loading-spinner" />
      <span>加载中...</span>
    </div>
  )
}

function ErrorBox({ message, onRetry }) {
  return (
    <div className="admin-error-box">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <span>{message}</span>
      {onRetry && <button className="admin-retry-btn" onClick={onRetry}>重试</button>}
    </div>
  )
}

function StatusDot({ ok }) {
  return <span className={`admin-status-dot${ok ? ' ok' : ' err'}`} />
}

function DashboardTab({ stats, loading, error, onRetry }) {
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} onRetry={onRetry} />

  const s = stats || {}

  return (
    <div className="admin-dashboard">
      <div className="admin-stat-cards">
        <div className="admin-stat-card">
          <div className="admin-stat-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </div>
          <div className="admin-stat-value">{s.total_users ?? '—'}</div>
          <div className="admin-stat-label">总用户数</div>
        </div>

        <div className="admin-stat-card">
          <div className="admin-stat-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="admin-stat-value">{s.today_active_users ?? '—'}</div>
          <div className="admin-stat-label">今日活跃用户</div>
        </div>

        <div className="admin-stat-card">
          <div className="admin-stat-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <div className="admin-stat-value">{s.total_reading_records ?? '—'}</div>
          <div className="admin-stat-label">总阅读记录</div>
        </div>
      </div>

      <div className="admin-status-row">
        <div className="admin-status-card">
          <div className="admin-status-header">
            <StatusDot ok={s.database_status === 'connected'} />
            <span>数据库</span>
          </div>
          <span className={`admin-status-text${s.database_status === 'connected' ? ' ok' : ' err'}`}>
            {s.database_status === 'connected' ? '正常' : s.database_status || '未知'}
          </span>
        </div>

        <div className="admin-status-card">
          <div className="admin-status-header">
            <StatusDot ok={s.dify_status === 'connected'} />
            <span>Dify AI</span>
          </div>
          <span className={`admin-status-text${s.dify_status === 'connected' ? ' ok' : ' err'}`}>
            {s.dify_status === 'connected' ? '正常' : s.dify_status || '未知'}
          </span>
        </div>
      </div>

      <button className="admin-refresh-btn" onClick={onRetry}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        刷新数据
      </button>
    </div>
  )
}

function UsersTab({ loading, error, usersData, page, onPageChange, onRetry }) {
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} onRetry={onRetry} />

  const data = usersData || {}
  const users = data.users || []
  const total = data.total ?? 0
  const totalPages = data.total_pages ?? 1
  const currentPage = data.page ?? page

  if (users.length === 0) {
    return (
      <div className="admin-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <p>暂无用户数据</p>
      </div>
    )
  }

  return (
    <div className="admin-users-wrap">
      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th>邮箱</th>
              <th>昵称</th>
              <th>角色</th>
              <th>注册时间</th>
              <th>过期时间</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className={u.is_admin ? 'admin-row-highlight' : ''}>
                <td className="admin-td-email" title={u.email}>{u.email}</td>
                <td>{u.display_name || '—'}</td>
                <td>
                  <span className={`admin-role-badge${u.is_admin ? ' admin' : ''}`}>
                    {u.is_admin ? '管理员' : '用户'}
                  </span>
                </td>
                <td className="admin-td-time">{formatTime(u.created_at)}</td>
                <td className="admin-td-time">{formatTime(u.expire_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="admin-pagination">
        <span className="admin-page-info">共 {total} 条，第 {currentPage}/{totalPages} 页</span>
        <div className="admin-page-btns">
          <button
            className="admin-page-btn"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            上一页
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
            <button
              key={p}
              className={`admin-page-btn${p === currentPage ? ' active' : ''}`}
              onClick={() => onPageChange(p)}
            >
              {p}
            </button>
          ))}
          <button
            className="admin-page-btn"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  )
}

function HealthTab({ health, loading, error, onRetry }) {
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} onRetry={onRetry} />

  const h = health || {}

  return (
    <div className="admin-health">
      <div className="admin-health-grid">
        <div className="admin-health-item">
          <span className="admin-health-label">API 版本</span>
          <span className="admin-health-value">{h.version || '—'}</span>
        </div>
        <div className="admin-health-item">
          <span className="admin-health-label">服务状态</span>
          <span className={`admin-health-value${h.status === 'ok' ? ' ok' : ' err'}`}>
            <StatusDot ok={h.status === 'ok'} />
            {h.status === 'ok' ? '正常' : h.status || '未知'}
          </span>
        </div>
        <div className="admin-health-item">
          <span className="admin-health-label">数据库连接</span>
          <span className={`admin-health-value${h.database === 'connected' ? ' ok' : ' err'}`}>
            <StatusDot ok={h.database === 'connected'} />
            {h.database || '—'}
          </span>
        </div>
        <div className="admin-health-item">
          <span className="admin-health-label">Dify 服务</span>
          <span className={`admin-health-value${h.dify === 'connected' ? ' ok' : ' err'}`}>
            <StatusDot ok={h.dify === 'connected'} />
            {h.dify || '—'}
          </span>
        </div>
        <div className="admin-health-item">
          <span className="admin-health-label">服务器时间</span>
          <span className="admin-health-value">{h.timestamp ? formatTime(h.timestamp) : '—'}</span>
        </div>
      </div>

      <button className="admin-refresh-btn" onClick={onRetry}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        刷新
      </button>
    </div>
  )
}

export default function AdminPanel({ onClose }) {
  const { user } = useAuth()
  const [tab, setTab] = useState('dashboard')

  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState(null)

  const [usersData, setUsersData] = useState(null)
  const [usersLoading, setUsersLoading] = useState(true)
  const [usersError, setUsersError] = useState(null)
  const [page, setPage] = useState(1)

  const [health, setHealth] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [healthError, setHealthError] = useState(null)

  const token = user?.token

  const fetchStats = () => {
    setStatsLoading(true)
    setStatsError(null)
    fetch('/api/admin/stats', {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => {
        if (!r.ok) {
          if (r.status === 401) return Promise.reject(new Error('登录已过期，请重新登录'))
          if (r.status === 403) return Promise.reject(new Error('无管理员权限'))
          return Promise.reject(new Error(`请求失败 (${r.status})`))
        }
        return r.json()
      })
      .then(data => { setStats(data); setStatsLoading(false) })
      .catch(err => { setStatsError(err.message); setStatsLoading(false) })
  }

  const fetchUsers = (p) => {
    setUsersLoading(true)
    setUsersError(null)
    fetch(`/api/admin/users?page=${p}&page_size=20`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => {
        if (!r.ok) {
          if (r.status === 401) return Promise.reject(new Error('登录已过期，请重新登录'))
          if (r.status === 403) return Promise.reject(new Error('无管理员权限'))
          return Promise.reject(new Error(`请求失败 (${r.status})`))
        }
        return r.json()
      })
      .then(data => { setUsersData(data); setUsersLoading(false) })
      .catch(err => { setUsersError(err.message); setUsersLoading(false) })
  }

  const fetchHealth = () => {
    setHealthLoading(true)
    setHealthError(null)
    fetch('/api/admin/health')
      .then(r => {
        if (!r.ok) return Promise.reject(new Error(`请求失败 (${r.status})`))
        return r.json()
      })
      .then(data => { setHealth(data); setHealthLoading(false) })
      .catch(err => { setHealthError(err.message); setHealthLoading(false) })
  }

  useEffect(() => { fetchStats() }, [])
  useEffect(() => { fetchUsers(page) }, [page])
  useEffect(() => { fetchHealth() }, [])

  // 非管理员
  if (!user?.is_admin) {
    return (
      <div className="admin-overlay">
        <div className="admin-panel">
          <div className="admin-header">
            <h2>管理后台</h2>
            <button className="admin-close-btn" onClick={onClose} aria-label="关闭">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div className="admin-forbidden">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
            </svg>
            <h3>无访问权限</h3>
            <p>仅管理员可访问管理后台</p>
          </div>
        </div>
      </div>
    )
  }

  const tabs = [
    { key: 'dashboard', label: '系统概览' },
    { key: 'users', label: '用户列表' },
    { key: 'health', label: '健康检查' },
  ]

  return (
    <div className="admin-overlay" onClick={onClose}>
      <div className="admin-panel" onClick={e => e.stopPropagation()}>
        <div className="admin-header">
          <div className="admin-header-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <h2>管理后台</h2>
          </div>
          <button className="admin-close-btn" onClick={onClose} aria-label="关闭">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <nav className="admin-nav">
          {tabs.map(t => (
            <button
              key={t.key}
              className={`admin-nav-btn${tab === t.key ? ' active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="admin-body">
          {tab === 'dashboard' && (
            <DashboardTab
              stats={stats}
              loading={statsLoading}
              error={statsError}
              onRetry={fetchStats}
            />
          )}

          {tab === 'users' && (
            <UsersTab
              loading={usersLoading}
              error={usersError}
              usersData={usersData}
              page={page}
              onPageChange={setPage}
              onRetry={() => fetchUsers(page)}
            />
          )}

          {tab === 'health' && (
            <HealthTab
              health={health}
              loading={healthLoading}
              error={healthError}
              onRetry={fetchHealth}
            />
          )}
        </div>
      </div>
    </div>
  )
}
