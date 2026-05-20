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
      <div className="login-card">
        <div className="login-header">
          <h1>名著导读</h1>
          <span className="beta-badge">测试版</span>
        </div>
        <p className="beta-notice">新注册账号有效期30分钟，过期自动删除</p>
        <p className="login-subtitle">{isLogin ? '登录账号' : '创建账号'}</p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="邮箱"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="密码（至少6位）"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
          />
          {!isLogin && (
            <input
              type="text"
              placeholder="显示名称（选填）"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
            />
          )}
          {error && <div className="login-error">{error}</div>}
          <button type="submit" disabled={submitting}>
            {submitting ? '处理中...' : (isLogin ? '登录' : '注册')}
          </button>
        </form>
        <p className="login-toggle">
          {isLogin ? '没有账号？' : '已有账号？'}
          <button className="link-btn" onClick={toggle}>
            {isLogin ? '去注册' : '去登录'}
          </button>
        </p>
        <div className="login-download">
          <a href="/mingzhu.apk" download className="apk-download-btn">📱 下载Android App</a>
        </div>
      </div>
    </div>
  )
}
