import { useState } from 'react'
import './App.css'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/atom-one-light.css'

interface Feedback {
  filename: string
  assignment: string
  path: string
}

interface FeedbackContent {
  student_id: string
  assignment: string
  filename: string
  content: string
}

function App() {
  const [studentId, setStudentId] = useState('')
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([])
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackContent | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async () => {
    if (!studentId.trim()) {
      setError('请输入学号')
      return
    }

    setLoading(true)
    setError('')
    setSelectedFeedback(null)

    try {
      const response = await fetch(`http://localhost:8000/api/feedback/${studentId}`)
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('未找到该学号的反馈报告')
        } else {
          setError('获取反馈报告失败')
        }
        setFeedbacks([])
        return
      }

      const data = await response.json()
      setFeedbacks(data.feedbacks || [])
    } catch (err) {
      setError('网络错误，请确保后端服务已启动')
      setFeedbacks([])
    } finally {
      setLoading(false)
    }
  }

  const handleViewFeedback = async (assignment: string) => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`http://localhost:8000/api/feedback/${studentId}/${assignment}`)
      
      if (!response.ok) {
        setError('获取反馈内容失败')
        return
      }

      const data = await response.json()
      setSelectedFeedback(data)
    } catch (err) {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>📚 TA Agent</h1>
        <p>作业反馈查询系统</p>
      </header>

      <div className="main-layout">
        {/* 左侧搜索和列表区域 */}
        <aside className="sidebar">
          <div className="search-section">
            <h2 className="sidebar-title">查询反馈</h2>
            <div className="search-box">
              <input
                type="text"
                placeholder="输入学号 (例如: 12210211)"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="search-input"
              />
              <button 
                onClick={handleSearch} 
                disabled={loading}
                className="search-button"
              >
                {loading ? '🔄' : '🔍'}
              </button>
            </div>

            {error && <div className="error-message">{error}</div>}
          </div>

          {feedbacks.length > 0 && (
            <div className="feedback-list">
              <h3 className="list-title">找到 {feedbacks.length} 份报告</h3>
              <div className="feedback-items">
                {feedbacks.map((feedback) => (
                  <div 
                    key={feedback.filename} 
                    className={`feedback-item ${selectedFeedback?.assignment === feedback.assignment ? 'active' : ''}`}
                    onClick={() => handleViewFeedback(feedback.assignment)}
                  >
                    <div className="item-icon">📄</div>
                    <div className="item-info">
                      <div className="item-title">{feedback.assignment.toUpperCase()}</div>
                      <div className="item-subtitle">{feedback.filename}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* 右侧内容显示区域 */}
        <main className="content-area">
          {selectedFeedback ? (
            <div className="feedback-content">
              <div className="feedback-header">
                <div>
                  <h2>反馈报告</h2>
                  <p className="assignment-name">{selectedFeedback.assignment.toUpperCase()}</p>
                </div>
                <button
                  onClick={() => setSelectedFeedback(null)}
                  className="close-button"
                  title="关闭"
                >
                  ✕
                </button>
              </div>
              <div className="markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {selectedFeedback.content}
                </ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <h2>欢迎使用 TA Agent</h2>
              <p>请在左侧输入学号查询反馈报告</p>
              <p className="empty-hint">然后点击列表中的作业查看详细反馈</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
