import { useState, useRef, useEffect } from 'react'
import { useAuth } from './AuthContext'
import Login from './Login'
import './design-system.css'
import './App.css'
import SearchBox from './components/SearchBox'
import AdminPanel from './AdminPanel'

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
  const [availableBooks, setAvailableBooks] = useState(null)
  const [conversations, setConversations] = useState(initConversations)
  const [activeConvId, setActiveConvId] = useState(null)
  const [speaking, setSpeaking] = useState('idle')
  const [speakingPara, setSpeakingPara] = useState(-1)
  const speakingRef = useRef('idle')
  const paraIdxRef = useRef(-1)

  // ── 深色模式 ──
  const [theme, setTheme] = useState(() => {
    try {
      const stored = localStorage.getItem('mingzhu_theme')
      if (stored === 'dark' || stored === 'light') return stored
    } catch {}
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  // ── 移动端 ──
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  const [showAdminPanel, setShowAdminPanel] = useState(false)

  const chatEnd = useRef(null)
  const contentRef = useRef(null)
  const convIdRef = useRef(null)
  const messagesRef = useRef(messages)
  const newConvIdRef = useRef(null)
  const progressTimerRef = useRef(null)
  const pendingConvRestore = useRef(true)
  const pendingChRestore = useRef(true)
  const chRestoreIdx = useRef(initProgress.chapterIdx)

  useEffect(() => { messagesRef.current = messages }, [messages])

  const cfg = WORKS[work] || { baseUrl: '/api', questions: [] }

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

    stopSpeech()
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

  // 从 API 获取可用书籍列表（fallback 到 WORKS）
  useEffect(() => {
    fetch('/api/chapters/books')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        let books = null
        if (data.books && Array.isArray(data.books)) books = data.books
        else if (Array.isArray(data)) books = data
        if (books && books.length > 0) setAvailableBooks(books)
      })
      .catch(() => {})
  }, [])

  // 服务端恢复阅读进度（优先级高于 localStorage）
  useEffect(() => {
    if (!user?.token) return
    fetch('/api/reading/last', {
      headers: { 'Authorization': `Bearer ${user.token}` }
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        if (data.book && data.chapter_idx != null && data.chapter_idx >= 0) {
          if (data.book !== work) {
            saveConv()
            setWork(data.book)
          }
          chRestoreIdx.current = data.chapter_idx
          pendingChRestore.current = true
        }
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.token])

  // 阅读进度同步到服务端（2 秒防抖）
  useEffect(() => {
    if (chapterIdx < 0 || !user?.token || chapters.length === 0) return
    if (progressTimerRef.current) clearTimeout(progressTimerRef.current)
    progressTimerRef.current = setTimeout(() => {
      const ch = chapters[chapterIdx]
      if (!ch) return
      fetch('/api/reading/progress', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({ book: work, chapter_id: ch.id, chapter_idx: chapterIdx })
      }).catch(() => {})
    }, 2000)
    return () => {
      if (progressTimerRef.current) clearTimeout(progressTimerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterIdx, work, chapters.length > 0 ? chapters[chapterIdx]?.id : null, user?.token])

  // ── 主题应用 ──
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem('mingzhu_theme', theme) } catch {}
    // 首次渲染后启用过渡
    setTimeout(() => document.body.classList.add('theme-transition-enabled'), 100)
  }, [theme])

  // ── 系统主题偏好监听 ──
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e) => {
      try {
        if (!localStorage.getItem('mingzhu_theme')) {
          setTheme(e.matches ? 'dark' : 'light')
        }
      } catch {}
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  // ── 移动端宽度监听 ──
  useEffect(() => {
    const handler = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (!mobile) setMobileMenuOpen(false)
    }
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

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
    stopSpeech()
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

  function stopSpeech(keepPos) {
    speakingRef.current = 'idle'
    window.speechSynthesis.cancel()
    setSpeaking('idle')
    if (!keepPos) {
      paraIdxRef.current = -1
      setSpeakingPara(-1)
    }
  }

  function pauseSpeech() {
    window.speechSynthesis.pause()
    speakingRef.current = 'paused'
    setSpeaking('paused')
  }

  function resumeSpeech() {
    window.speechSynthesis.resume()
    speakingRef.current = 'playing'
    setSpeaking('playing')
  }

  function startSpeech(fromIdx = 0) {
    if (!chapterContent) return
    const synth = window.speechSynthesis
    synth.cancel()
    speakingRef.current = 'playing'
    setSpeaking('playing')

    const paras = chapterContent.split('\n')
    if (!paras.some(p => p.trim())) return

    let idx = fromIdx
    let lastNonEmpty = paras.length - 1
    while (lastNonEmpty >= 0 && !paras[lastNonEmpty].trim()) lastNonEmpty--

    function speakNext() {
      while (idx < paras.length && !paras[idx].trim()) idx++
      if (idx >= paras.length || speakingRef.current !== 'playing') {
        if (speakingRef.current === 'playing') { speakingRef.current = 'idle'; setSpeaking('idle'); setSpeakingPara(-1) }
        return
      }
      const cur = idx
      const isLast = cur >= lastNonEmpty
      const u = new SpeechSynthesisUtterance(paras[cur])
      u.lang = 'zh-CN'
      u.rate = 0.9
      u.onstart = () => { paraIdxRef.current = cur; setSpeakingPara(cur) }
      u.onend = () => {
        if (isLast) { speakingRef.current = 'idle'; setSpeaking('idle'); setSpeakingPara(-1); return }
        idx++; speakNext()
      }
      u.onerror = () => {
        if (isLast) { speakingRef.current = 'idle'; setSpeaking('idle'); setSpeakingPara(-1); return }
        idx++; speakNext()
      }
      synth.speak(u)
    }
    speakNext()
  }

  function paraIdxAtClientX(clientX, el) {
    const rect = el.getBoundingClientRect()
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    const target = Math.floor(pct * chapterNonEmptyParas)
    let count = 0
    for (let i = 0; i < chapterAllParas.length; i++) {
      if (chapterAllParas[i].trim()) {
        if (count === target) return i
        count++
      }
    }
    return chapterAllParas.length - 1
  }

  function getClientX(e, currentTarget) {
    if (e.touches) return e.touches[0]?.clientX || e.clientX
    return e.clientX
  }

  function onProgressDown(e) {
    const clientX = getClientX(e, e.currentTarget)
    const idx = paraIdxAtClientX(clientX, e.currentTarget)
    const wasPlaying = speakingRef.current !== 'idle'
    stopSpeech(true)
    setSpeakingPara(idx)
    paraIdxRef.current = idx

    const handleMove = (ev) => {
      const cx = getClientX(ev, e.currentTarget)
      const i = paraIdxAtClientX(cx, e.currentTarget)
      paraIdxRef.current = i
      setSpeakingPara(i)
    }
    const handleUp = () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
      window.removeEventListener('touchmove', handleMove)
      window.removeEventListener('touchend', handleUp)
      if (wasPlaying) startSpeech(paraIdxRef.current)
    }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    window.addEventListener('touchmove', handleMove, { passive: false })
    window.addEventListener('touchend', handleUp)
  }

  function toggleSpeech() {
    if (speakingRef.current === 'playing') { pauseSpeech(); return }
    if (speakingRef.current === 'paused') { resumeSpeech(); return }
    startSpeech(0)
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

  function toggleTheme() {
    setTheme(t => t === 'dark' ? 'light' : 'dark')
  }

  function handleChapterSelect(idx) {
    loadChapter(idx)
    if (isMobile) setMobileMenuOpen(false)
  }

  const curChapter = chapterIdx >= 0 ? chapters[chapterIdx] : null
  const chapterAllParas = chapterContent ? chapterContent.split('\n') : []
  const chapterNonEmptyParas = chapterAllParas.filter(p => p.trim()).length
  const spokenNonEmpty = chapterAllParas.slice(0, speakingPara + 1).filter(p => p.trim()).length
  const workConvs = conversations[work] || []
  const sortedConvs = [...workConvs].reverse()

  return (
    <div className="app">
      {isMobile && (
        <div className={`mobile-overlay-backdrop${mobileMenuOpen ? ' show' : ''}`} onClick={() => setMobileMenuOpen(false)} />
      )}
      <aside className={`reader-panel${isMobile && mobileMenuOpen ? ' mobile-open' : ''}`}>
        <div className="reader-toolbar">
          <SearchBox book={work} chapters={chapters} onSelectChapter={handleChapterSelect} />
          <select className="work-select" value={work} onChange={e => { saveConv(); setWork(e.target.value); if (isMobile) setMobileMenuOpen(false) }} aria-label="选择名著">
            {(availableBooks && availableBooks.length > 0 ? availableBooks : Object.keys(WORKS)).map(w => <option key={w}>{w}</option>)}
          </select>
          {chapters.length > 0 && (
            <select
              className="chapter-select"
              value={chapterIdx}
              onChange={e => handleChapterSelect(parseInt(e.target.value))}
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
              <button onClick={() => handleChapterSelect(chapterIdx - 1)} disabled={chapterIdx <= 0} title="上一回">&#x25C2;</button>
              <span className="chapter-nav-info">{chapterIdx >= 0 ? `${chapterIdx + 1}/${chapters.length}` : ''}</span>
              <button onClick={() => handleChapterSelect(chapterIdx + 1)} disabled={chapterIdx >= chapters.length - 1} title="下一回">&#x25B8;</button>
            </div>
          )}
          {chapterContent && !chapterLoading && (
            <div className="tts-controls">
              <button className="tts-btn" onClick={toggleSpeech} title={speaking === 'playing' ? '暂停' : speaking === 'paused' ? '继续' : '朗读'}>
                {speaking === 'playing' ? '⏸' : speaking === 'paused' ? '▶' : '🔊'}
              </button>
              {speaking !== 'idle' && (
                <button className="tts-btn tts-stop" onClick={stopSpeech} title="停止">⏹</button>
              )}
              {chapterNonEmptyParas > 0 && (
                <span className="tts-progress-wrap">
                  <span className="tts-progress-bar" onMouseDown={onProgressDown} onTouchStart={onProgressDown} title="拖动跳转">
                    <span className="tts-progress-fill" style={{ width: `${speakingPara >= 0 ? (spokenNonEmpty / chapterNonEmptyParas * 100) : 0}%` }} />
                  </span>
                  <span className="tts-progress">{speakingPara >= 0 ? spokenNonEmpty : 0}/{chapterNonEmptyParas}</span>
                </span>
              )}
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
                  <button key={ch.id} className="chapter-quick-item" onClick={() => handleChapterSelect(i)}>
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
                para.trim() ? (
                  <p key={i} className={speakingPara === i ? 'tts-active' : ''} ref={el => {
                    if (el && speakingPara === i && speakingRef.current === 'playing') el.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  }}>{para}</p>
                ) : <br key={i} />
              )}
            </div>
          )}
        </div>
      </aside>

      <main className="chat-panel">
        <header className="header">
          {isMobile && (
            <button className="hamburger-btn" onClick={() => setMobileMenuOpen(true)} aria-label="打开菜单">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          )}
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
            {user.is_admin && (
              <button className="theme-toggle-btn" onClick={() => setShowAdminPanel(true)} aria-label="管理后台" title="管理后台">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </button>
            )}
            <button className="theme-toggle-btn" onClick={toggleTheme} aria-label="切换深色/浅色主题">
              {theme === 'dark' ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5"/>
                  <line x1="12" y1="1" x2="12" y2="3"/>
                  <line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/>
                  <line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>
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

      {showAdminPanel && <AdminPanel onClose={() => setShowAdminPanel(false)} />}
    </div>
  )
}
