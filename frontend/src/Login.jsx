import { useState } from 'react'
import { useAuth } from './AuthContext'
import './Login.css'

export default function Login() {
  const { login, register } = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (isLogin) {
        await login(email, password)
      } else {
        await register(email, password, displayName)
      }
    } catch (err) {
      setError(err.message)
    }
    setSubmitting(false)
  }

  function toggle() {
    setError('')
    setIsLogin(!isLogin)
  }

  return (
    <div className="login-page">
      <div className="login-brand">
        <h1>名著导读</h1>
        <p className="subtitle">AI 驱动的四大名著交互阅读平台</p>
        <span className="divider" />
      </div>

      <div className="login-card">
        <h2>
          {isLogin ? '登录' : '创建账号'}
          <span className="beta-badge">测试版</span>
        </h2>
        <p className="beta-notice">新注册账号有效期30分钟，过期自动删除</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="login-email">邮箱</label>
            <input
              id="login-email"
              type="email"
              placeholder="请输入邮箱地址"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">密码</label>
            <input
              id="login-password"
              type="password"
              placeholder="请输入密码（至少6位）"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label htmlFor="login-name">显示名称</label>
              <input
                id="login-name"
                type="text"
                placeholder="选填，公开显示的名称"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                autoComplete="name"
              />
            </div>
          )}

          {error && <div className="login-error" role="alert">{error}</div>}

          <button type="submit" disabled={submitting}>
            {submitting ? '处理中...' : (isLogin ? '登录' : '注册')}
          </button>
        </form>

        <p className="login-toggle">
          {isLogin ? '没有账号？' : '已有账号？'}
          <button className="link-btn" onClick={toggle} type="button">
            {isLogin ? '去注册' : '去登录'}
          </button>
        </p>

        <div className="login-download">
          <a href="/mingzhu.apk" download className="apk-download-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12" y2="18"/><polyline points="8 12 12 16 16 12"/></svg>
            下载 Android App
          </a>
        </div>
      </div>
    </div>
  )
}
