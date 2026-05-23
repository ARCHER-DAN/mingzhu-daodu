import { useState, useRef, useEffect } from 'react'
import { useAuth } from './AuthContext'
import Login from './Login'
import './design-system.css'
import './App.css'

const WORKS = {
  '西游记': {
    baseUrl: '/api',
    questions: [
      '孙悟空有哪些经典故事？',
      '唐僧的性格特点是什么？',
      '大闹天宫是怎么回事？',
      '西游记的作者是谁？',
      '请简单介绍一下取经团队',
    ],
  },
  '三国演义': {
    baseUrl: '/api',
    questions: ['诸葛亮草船借箭是怎么回事？', '关羽温酒斩华雄的故事', '刘备三顾茅庐的经过', '赤壁之战的故事梗概', '曹操的性格特点分析'],
  },
  '红楼梦': {
    baseUrl: '/api',
    questions: ['林黛玉进贾府的故事', '贾宝玉梦游太虚幻境', '王熙凤的性格特点', '金陵十二钗都有谁？', '红楼梦的作者是谁？'],
  },
  '水浒传': {
    baseUrl: '/api',
    questions: ['武松打虎的故事', '林冲被逼上梁山的经过', '宋江的性格特点', '一百零八将的来历', '鲁智深倒拔垂杨柳'],
  },
}

const isInApp = new URLSearchParams(window.location.search).get('from') === 'app'

function fmtTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    const now = Date.now()
    const diff = now - d.getTime()
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
    return (d.getMonth() + 1) + '/' + d.getDate()
  } catch { return '' }
}

function enforceTotalLimit(convs) {
  const flat = []
  for (const w of Object.keys(convs)) {
    for (const c of (convs[w] || [])) {
      flat.push({ w, c })
    }
  }
  if (flat.length <= 50) return convs
  flat.sort((a, b) => new Date(b.c.createdAt) - new Date(a.c.createdAt))
  const kept = flat.slice(0, 50)
  const result = {}
  for (const { w, c } of kept) {
    if (!result[w]) result[w] = []
    result[w].push(c)
  }
  return result
}

export default function App() {
  const { user, loading, logout } = useAuth()

  const initProgress = (() => {
    try {
      const p = JSON.parse(localStorage.getItem('mingzhu_reading_progress'))
      return { work: p?.work || '西游记', chapterIdx: p?.chapterIdx ?? -1 }
    } catch { return { work: '西游记', chapterIdx: -1 } }
  })()

  const initConversations = (() => {
    try { return JSON.parse(localStorage.getItem('mingzhu_conversations')) || {} }
    catch { return {} }
  })()

  const [work, setWork] = useState(initProgress.work)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [feedback, setFeedback] = useState({})
  const [chapters, setChapters] = useState([])
  const [chapterIdx, setChapterIdx] = useState(initProgress.chapterIdx)
  const [chapterContent, setChapterContent] = useState('')
  const [chapterLoading, setChapterLoading] = useState(false)
  const [conversations, setConversations] = useState(initConversations)
  const [activeConvId, setActiveConvId] = useState(null)

  const chatEnd = useRef(null)
  const contentRef = useRef(null)
  const convIdRef = useRef(null)
  const messagesRef = useRef(messages)
  const newConvIdRef = useRef(null)
  const pendingConvRestore = useRef(true)    // 挂载/切作品时恢复最近对话
  const pendingChRestore = useRef(true)      // 挂载/切作品时恢复章节进度
  const chRestoreIdx = useRef(initProgress.chapterIdx)  // 初始/上一作品的章节进度

  useEffect(() => { messagesRef.current = messages }, [messages])

  const cfg = WORKS[work]

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    localStorage.setItem('mingzhu_conversations', JSON.stringify(conversations))
  }, [conversations])

  useEffect(() => {
    // 切换作品前保存当前阅读进度，读取新作品的 saved 进度
    try {
      const p = JSON.parse(localStorage.getItem('mingzhu_reading_progress'))
      if (p && p.work === work) chRestoreIdx.current = p.chapterIdx ?? -1
      else chRestoreIdx.current = -1
    } catch { chRestoreIdx.current = -1 }

    setMessages([])
    setActiveConvId(null)
    convIdRef.current = null
    setChapters([])
    setChapterIdx(-1)
    setChapterContent('')
    pendingConvRestore.current = true
    pendingChRestore.current = true
    fetchChapters(work)
  }, [work])

  // 作品切换/挂载后自动恢复最近对话
  useEffect(() => {
    if (!pendingConvRestore.current) return
    const workConvs = conversations[work] || []
    if (workConvs.length > 0) {
      const sorted = [...workConvs].sort((a, b) =>
        new Date(b.createdAt) - new Date(a.createdAt)
      )
      const latest = sorted[0]
      if (latest) {
        setMessages(latest.messages)
        convIdRef.current = latest.convId || null
        setActiveConvId(latest.id)
      }
    }
    pendingConvRestore.current = false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [work, conversations])

  // 章节加载后恢复之前保存的阅读进度（用 ref 避免被 effect 覆盖）
  useEffect(() => {
    if (!pendingChRestore.current) return
    if (chapters.length > 0 && chRestoreIdx.current >= 0 && chRestoreIdx.current < chapters.length) {
      pendingChRestore.current = false
      loadChapter(chRestoreIdx.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapters])

  if (loading) return (
    <div className="loading" role="status" aria-label="加载中">
      <div className="loading-spinner" />
      <span>加载中...</span>
    </div>
  )

  if (!user) return <Login />

  async function fetchChapters(book) {
    try {
      const res = await fetch(`/api/chapters?book=${encodeURIComponent(book)}`)
      const data = await res.json()
      if (data.chapters) setChapters(data.chapters)
    } catch {}
  }

  async function loadChapter(idx) {
    if (idx < 0 || idx >= chapters.length) return
    setChapterIdx(idx)
    chRestoreIdx.current = idx
    localStorage.setItem('mingzhu_reading_progress', JSON.stringify({ work, chapterIdx: idx }))
    setChapterLoading(true)
    setChapterContent('')
    try {
      const ch = chapters[idx]
      const res = await fetch(`/api/chapters?book=${encodeURIComponent(work)}&chapter=${ch.id}`)
      const data = await res.json()
      if (data.content) setChapterContent(data.content)
    } catch {}
    setChapterLoading(false)
  }

  function saveConv() {
    const msgs = messagesRef.current
    if (msgs.length === 0) return
    setConversations(prev => {
      const workConvs = [...(prev[work] || [])]
      let limited = [...msgs]
      if (limited.length > 50) limited = limited.slice(limited.length - 50)
      if (activeConvId) {
        const idx = workConvs.findIndex(c => c.id === activeConvId)
        if (idx >= 0) {
          workConvs[idx] = { ...workConvs[idx], messages: limited, convId: convIdRef.current || workConvs[idx].convId }
        }
      } else {
        const newId = Date.now()
        newConvIdRef.current = newId
        const title = msgs.find(m => m.role === 'user')?.content || '新对话'
        workConvs.push({
          id: newId,
          title: title.slice(0, 50),
          messages: limited,
          convId: convIdRef.current,
          createdAt: new Date().toISOString(),
        })
      }
      return enforceTotalLimit({ ...prev, [work]: workConvs })
    })
    if (newConvIdRef.current) {
      setActiveConvId(newConvIdRef.current)
      newConvIdRef.current = null
    }
  }

  function switchConv(convId) {
    if (streaming) return
    saveConv()
    const conv = (conversations[work] || []).find(c => c.id === convId)
    if (!conv) return
    setMessages(conv.messages)
    convIdRef.current = conv.convId || null
    setActiveConvId(convId)
  }

  function newConv() {
    if (streaming) return
    saveConv()
    setMessages([])
    setActiveConvId(null)
    convIdRef.current = null
  }

  async function send(query) {
    const q = query || input.trim()
    if (!q || streaming) return
    setInput('')
    setStreaming(true)

    const userMsg = { role: 'user', content: q }
    const aiMsg = { role: 'ai', content: '', id: Date.now() }
    setMessages(prev => [...prev, userMsg, aiMsg])

    try {
      const res = await fetch(`${cfg.baseUrl}/chat-messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          response_mode: 'streaming',
          user: `user-${user.id}`,
          inputs: {},
          conversation_id: convIdRef.current || undefined,
        }),
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
              setMessages(prev => prev.map(m =>
                m.id === aiMsg.id ? { ...m, content: full } : m
              ))
            } else if (evt.event === 'message_end') {
              if (evt.conversation_id) convIdRef.current = evt.conversation_id
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
    saveConv()
  }

  function toggleFeedback(msgId, type) {
    setFeedback(prev => ({ ...prev, [msgId]: prev[msgId] === type ? null : type }))
  }

  const curChapter = chapterIdx >= 0 ? chapters[chapterIdx] : null
  const workConvs = conversations[work] || []
  const sortedConvs = [...workConvs].reverse()

  return (
    <div className="app">
      <aside className="reader-panel">
        <div className="reader-toolbar">
          <select className="work-select" value={work} onChange={e => { saveConv(); setWork(e.target.value) }} aria-label="选择名著">
            {Object.keys(WORKS).map(w => <option key={w}>{w}</option>)}
          </select>
          {chapters.length > 0 && (
            <select
              className="chapter-select"
              value={chapterIdx}
              onChange={e => loadChapter(parseInt(e.target.value))}
              aria-label="选择章节"
            >
              <option value={-1}>— 选择章节 —</option>
              {chapters.map((ch, i) => (
                <option key={ch.id} value={i}>第{ch.id}回 {ch.title}</option>
              ))}
            </select>
          )}
          {chapters.length > 0 && (
            <div className="chapter-nav">
              <button onClick={() => loadChapter(chapterIdx - 1)} disabled={chapterIdx <= 0} title="上一回">&#x25C2;</button>
              <span className="chapter-nav-info">{chapterIdx >= 0 ? `${chapterIdx + 1}/${chapters.length}` : ''}</span>
              <button onClick={() => loadChapter(chapterIdx + 1)} disabled={chapterIdx >= chapters.length - 1} title="下一回">&#x25B8;</button>
            </div>
          )}
        </div>

        <div className="reader-content" ref={contentRef}>
          {chapters.length === 0 && (
            <div className="reader-empty">
              <div className="reader-empty-icon">书</div>
              <p>该名著原文数据尚未收录</p>
            </div>
          )}
          {chapters.length > 0 && chapterIdx === -1 && (
            <div className="reader-empty">
              <div className="reader-empty-icon">目</div>
              <p>请选择章节开始阅读</p>
              <div className="chapter-quick-list">
                {chapters.slice(0, 20).map((ch, i) => (
                  <button key={ch.id} className="chapter-quick-item" onClick={() => loadChapter(i)}>
                    第{ch.id}回 {ch.title}
                  </button>
                ))}
                {chapters.length > 20 && <span className="chapter-quick-more">……共{chapters.length}回，请从上方选择</span>}
              </div>
            </div>
          )}
          {chapterLoading && (
            <div className="reader-loading">
              <div className="loading-spinner" />
              <span>加载中...</span>
            </div>
          )}
          {chapterContent && !chapterLoading && (
            <div className="chapter-text">
              <h2 className="chapter-title">第{curChapter.id}回 {curChapter.title}</h2>
              {chapterContent.split('\n').map((para, i) =>
                para.trim() ? <p key={i}>{para}</p> : <br key={i} />
              )}
            </div>
          )}
        </div>
      </aside>

      <main className="chat-panel">
        <header className="header">
          <div className="header-brand">
            <h1>名著导读</h1>
            {isInApp && <span className="version-tag">v2.0.4</span>}
          </div>
          <div className="header-controls">
            <span className="user-name">{user.display_name || user.email}</span>
            {!isInApp && (
              <a href="/mingzhu.apk" download className="apk-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><polyline points="8 12 12 16 16 12"/></svg>
                下载App
              </a>
            )}
            <button className="logout-btn" onClick={logout}>退出</button>
          </div>
        </header>

        <div className="conv-bar">
          <button className="conv-new-btn" onClick={newConv} disabled={streaming} title="新建对话">+</button>
          <div className="conv-list">
            {sortedConvs.map(conv => (
              <button
                key={conv.id}
                className={`conv-item${conv.id === activeConvId ? ' active' : ''}`}
                onClick={() => switchConv(conv.id)}
                disabled={streaming}
                title={conv.title}
              >
                <span className="conv-item-title">{conv.title.slice(0, 20)}</span>
                <span className="conv-item-time">{fmtTime(conv.createdAt)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="chat-area" role="log" aria-label="聊天记录">
          {messages.length === 0 && (
            <div className="welcome">
              <div className="welcome-icon">卷</div>
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
              <div className="msg-avatar" aria-hidden="true">{m.role === 'user' ? '我' : 'AI'}</div>
              <div className="msg-body">
                <div className={`msg-text${m.role === 'ai' && !m.content && streaming ? ' streaming' : ''}`}>
                  {m.content || (m.role === 'ai' && streaming ? '' : '')}
                </div>
                {m.role === 'ai' && m.content && (
                  <div className="msg-actions">
                    <button
                      className={`fb${feedback[m.id] === 'like' ? ' active' : ''}`}
                      data-type="like"
                      onClick={() => toggleFeedback(m.id, 'like')}
                      aria-label="点赞"
                    >&#x1F44D;</button>
                    <button
                      className={`fb${feedback[m.id] === 'dislike' ? ' active' : ''}`}
                      data-type="dislike"
                      onClick={() => toggleFeedback(m.id, 'dislike')}
                      aria-label="点踩"
                    >&#x1F44E;</button>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEnd} />
        </div>

        <footer className="input-bar">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="输入问题，按回车发送..."
            disabled={streaming}
            aria-label="输入消息"
          />
          <button onClick={() => send()} disabled={streaming}>
            {streaming ? '发送中' : '发送'}
          </button>
        </footer>
      </main>
    </div>
  )
}
