import { useState, useRef, useEffect, useCallback } from 'react'

export default function SearchBox({ book, chapters, onSelectChapter }) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const inputRef = useRef(null)
  const containerRef = useRef(null)

  // 点击外部关闭
  useEffect(() => {
    if (!isOpen) return
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        closeSearch()
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

  // 展开时自动聚焦输入框
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  function closeSearch() {
    setIsOpen(false)
    setResults([])
    setSearched(false)
    setQuery('')
  }

  const doSearch = useCallback(async (q) => {
    if (!q.trim() || !book) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await fetch(`/api/chapters/search?book=${encodeURIComponent(book)}&q=${encodeURIComponent(q.trim())}`)
      if (!res.ok) { setResults([]); setLoading(false); return }
      const data = await res.json()
      setResults(data.results || [])
    } catch {
      setResults([])
    }
    setLoading(false)
  }, [book])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      doSearch(query)
    } else if (e.key === 'Escape') {
      closeSearch()
    }
  }

  const handleResultClick = (result) => {
    const idx = chapters.findIndex(ch => String(ch.id) === String(result.chapter_id))
    if (idx >= 0) {
      onSelectChapter(idx)
    }
    closeSearch()
  }

  // 关键词高亮
  const highlight = (text, keyword) => {
    if (!keyword.trim()) return text
    const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const parts = text.split(new RegExp(`(${escaped})`, 'gi'))
    return parts.map((part, i) =>
      part.toLowerCase() === keyword.toLowerCase()
        ? <mark key={i} className="search-highlight">{part}</mark>
        : part
    )
  }

  return (
    <div className="search-box" ref={containerRef}>
      {!isOpen ? (
        <button
          className="search-toggle-btn"
          onClick={() => setIsOpen(true)}
          title="搜索章节内容"
          aria-label="打开搜索"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </button>
      ) : (
        <div className="search-expanded">
          <div className="search-input-row">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="search-input-icon">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              ref={inputRef}
              className="search-input"
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`搜索《${book}》...`}
              aria-label="搜索章节内容"
            />
            {query && (
              <button className="search-clear-btn" onClick={() => { setQuery(''); setResults([]); setSearched(false); inputRef.current?.focus() }} aria-label="清除">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            )}
            <button className="search-close-btn" onClick={closeSearch} aria-label="关闭搜索">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          {(loading || searched) && (
            <div className="search-results">
              {loading && (
                <div className="search-results-status">
                  <div className="loading-spinner" style={{ width: 16, height: 16 }} />
                  <span>搜索中...</span>
                </div>
              )}
              {!loading && searched && results.length === 0 && (
                <div className="search-results-empty">未找到相关内容</div>
              )}
              {!loading && results.length > 0 && (
                <div className="search-results-list">
                  {results.map((r, i) => (
                    <button
                      key={i}
                      className="search-result-item"
                      onClick={() => handleResultClick(r)}
                    >
                      <span className="search-result-title">
                        第{r.chapter_id}回 {r.chapter_title || ''}
                      </span>
                      {r.snippet && (
                        <span className="search-result-snippet">
                          {highlight(r.snippet.slice(0, 120), query)}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
