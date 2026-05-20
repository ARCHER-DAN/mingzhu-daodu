import { useState, useRef, useEffect } from 'react'
import { useAuth } from './AuthContext'
import Login from './Login'
import './App.css'

// Dify API 配置
const WORKS = {
  '西游记': {
    ''  // 从服务端 /api/config 获取,
    baseUrl: '/api',
    questions: [
      '孙悟空有哪些经典故事？',
      '唐僧的性格特点是什么？',
      '大闹天宫是怎么回事？',
      '西游记的作者是谁？',
      '请简单介绍一下取经团队',
    ],
  },
  '三国演义': { apiKey: '', baseUrl: '', questions: [] },
  '红楼梦':   { apiKey: '', baseUrl: '', questions: [] },
  '水浒传':   { apiKey: '', baseUrl: '', questions: [] },
}

const isInApp = new URLSearchParams(window.location.search).get('from') === 'app'

export default function App() {
  const { user, loading, logout } = useAuth()
  const [work, setWork] = useState('西游记')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [feedback, setFeedback] = useState({})
  const chatEnd = useRef(null)

  const cfg = WORKS[work]

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  if (loading) return <div className="loading">加载中...</div>
  if (!user) return <Login />

  async function send(query) {
    const q = query || input.trim()
    if (!q || streaming || !cfg.apiKey) return
    setInput('')
    setStreaming(true)

    const userMsg = { role: 'user', content: q }
    const aiMsg = { role: 'ai', content: '', id: Date.now() }
    setMessages(prev => [...prev, userMsg, aiMsg])

    try {
      const res = await fetch(`${cfg.baseUrl}/chat-messages`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, response_mode: 'streaming', user: `user-${user.id}`, inputs: {} }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let full = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value, { stream: true })
        for (const line of text.split('\n')) {
          if (!line.startsWith('data:')) continue
          try {
            const evt = JSON.parse(line.slice(5).trim())
            if (evt.event === 'message') {
              full += evt.answer || ''
            } else if (evt.event === 'message_end') {
              setMessages(prev => prev.map(m =>
                m.id === aiMsg.id ? { ...m, content: full, convId: evt.conversation_id } : m
              ))
            }
          } catch {}
        }
      }
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === aiMsg.id ? { ...m, content: '请求失败，请重试' } : m
      ))
    }
    setStreaming(false)
  }

  function toggleFeedback(msgId, type) {
    setFeedback(prev => ({ ...prev, [msgId]: prev[msgId] === type ? null : type }))
  }

  return (
    <div className="app">
      <header className="header">
        <h1>名著导读</h1>
        <div style={{display:'flex', gap:12, alignItems:'center'}}>
          <span className="user-name">{user.display_name || user.email}</span>
          {!isInApp && <a href="/mingzhu.apk" download className="apk-btn">📱下载App</a>}
          <select className="work-select" value={work} onChange={e => { setWork(e.target.value); setMessages([]) }}>
            {Object.keys(WORKS).map(w => <option key={w}>{w}</option>)}
          </select>
          <button className="logout-btn" onClick={logout}>退出</button>
        </div>
      </header>

      <main className="chat-area">
        {messages.length === 0 && (
          <div className="welcome">
            <h2>欢迎使用名著导读</h2>
            <p>选择一部名著，开始提问</p>
            <div className="suggested">
              {cfg.questions.map(q => (
                <button key={q} className="q-chip" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="msg-avatar">{m.role === 'user' ? '我' : 'AI'}</div>
            <div className="msg-body">
              <div className="msg-text">{m.content || (m.role === 'ai' && streaming ? '思考中...' : '')}</div>
              {m.role === 'ai' && m.content && (
                <div className="msg-actions">
                  <button className={`fb ${feedback[m.id] === 'like' ? 'active' : ''}`}
                    onClick={() => toggleFeedback(m.id, 'like')}>👍</button>
                  <button className={`fb ${feedback[m.id] === 'dislike' ? 'active' : ''}`}
                    onClick={() => toggleFeedback(m.id, 'dislike')}>👎</button>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={chatEnd} />
      </main>

      <footer className="input-bar">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="输入问题，按回车发送..."
          disabled={streaming || !cfg.apiKey}
        />
        <button onClick={() => send()} disabled={streaming || !cfg.apiKey}>
          {streaming ? '发送中' : '发送'}
        </button>
      </footer>
    </div>
  )
}
