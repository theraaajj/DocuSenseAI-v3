import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import {
  Send,
  Upload,
  Search,
  FolderPlus,
  Trash2,
  FileText,
  Database,
  ShieldCheck,
  Cpu,
  MoreHorizontal,
  Plus
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', content: "Hello! I'm DocuSenseAI. How can I assist you with your documents today?" }
  ]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('Uploaded Documents');
  const [isUploading, setIsUploading] = useState(false);
  const [allowedPaths, setAllowedPaths] = useState([]);
  const [newPath, setNewPath] = useState('');
  const [uploadStatus, setUploadStatus] = useState(null);
  const [selectedSource, setSelectedSource] = useState(null);
  const [indexedFiles, setIndexedFiles] = useState([]);

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
    fetchPaths();
    fetchFiles();
  }, [messages]);

  const fetchFiles = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/files`);
      setIndexedFiles(resp.data.files || []);
    } catch (e) {
      console.error("Failed to fetch files", e);
    }
  };

  const fetchPaths = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/disk/paths`);
      setAllowedPaths(resp.data.allowed_paths || []);
    } catch (e) {
      console.error("Failed to fetch paths", e);
    }
  };

  const handleSend = async () => {
    if (!query.trim() || loading) return;

    const userMsg = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const resp = await axios.post(`${API_BASE}/query`, {
        query: userMsg.content,
        mode: mode
      });

      setMessages(prev => [...prev, {
        role: 'ai',
        content: resp.data.answer,
        sources: resp.data.sources,
        grade_log: resp.data.grade_log
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'ai',
        content: `Error: ${err.response?.data?.detail || err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus("Uploading...");

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await axios.post(`${API_BASE}/upload`, formData);
      setUploadStatus(`Indexed ${resp.data.chunks} chunks.`);
      fetchFiles();
      setTimeout(() => setUploadStatus(null), 3000);
    } catch (err) {
      setUploadStatus("Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const addPath = async () => {
    if (!newPath) return;
    try {
      await axios.post(`${API_BASE}/disk/add-path`, { path: newPath });
      setNewPath('');
      fetchPaths();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to add path");
    }
  };

  const clearMemory = async () => {
    if (confirm("Reset everything?")) {
      await axios.delete(`${API_BASE}/memory`);
      setMessages([{ role: 'ai', content: "Memory cleared. How can I help?" }]);
      fetchPaths();
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <ShieldCheck className="logo-icon" />
          <h1 className="logo-text">DocuSenseAI</h1>
        </div>

        <div className="search-mode-toggle">
          <button
            className={`mode-btn ${mode === 'Uploaded Documents' ? 'active' : ''}`}
            onClick={() => setMode('Uploaded Documents')}
          >
            Uploads
          </button>
          <button
            className={`mode-btn ${mode === 'Local Disk Scout' ? 'active' : ''}`}
            onClick={() => setMode('Local Disk Scout')}
          >
            Disk Scout
          </button>
        </div>

        <div className="sidebar-section">
          <h3 className="section-title"><Upload size={14} /> Knowledge Ingestion</h3>
          <div className="upload-zone" onClick={() => fileInputRef.current.click()}>
            {isUploading ? (
              <div className="thinking"><div className="dot"></div><div className="dot"></div><div className="dot"></div></div>
            ) : (
              <>
                <Plus size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                <p style={{ margin: 0, fontSize: '0.85rem' }}>Drop or click to upload</p>
              </>
            )}
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={handleUpload}
            />
          </div>
          {uploadStatus && <p style={{ fontSize: '0.75rem', color: 'var(--primary-color)', marginTop: '8px' }}>{uploadStatus}</p>}

          {indexedFiles.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', fontWeight: 700 }}>Indexed Documents</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {indexedFiles.map((f, i) => (
                  <div key={i} className="source-badge" style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 8px' }}>
                    <FileText size={12} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="sidebar-section">
          <h3 className="section-title"><FolderPlus size={14} /> Active Folders</h3>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <input
              type="text"
              placeholder="C:/Path/To/Docs"
              className="main-input"
              style={{ padding: '8px', fontSize: '0.8rem' }}
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
            />
            <button className="send-button" style={{ width: '32px', height: '32px' }} onClick={addPath}>
              <Plus size={16} />
            </button>
          </div>
          <div className="path-list">
            {allowedPaths.map((p, i) => (
              <div key={i} className="source-badge" style={{ marginBottom: '4px', display: 'block' }}>{p}</div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 'auto' }}>
          <button className="btn-secondary" onClick={clearMemory}>
            <Trash2 size={16} /> Forget All Data
          </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="main-content">
        <header style={{ padding: '1rem 2rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>{mode}</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>Agentic CRAG v2.0</p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div className="source-badge">Local LLM: Phi-3</div>
            <div className="source-badge">Embedding: Nomic</div>
          </div>
        </header>

        <div className="chat-history">
          {messages.length === 0 && (
            <div className="empty-state">
              <Cpu size={48} opacity={0.2} />
              <p>Ready to analyze your documents locally.</p>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`message ${msg.role}`}
              >
                <div className="msg-bubble">
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>

                      {/* Reasoning Trace (Matches Streamlit functionality) */}
                      {msg.grade_log && msg.grade_log.length > 0 && (
                        <div className="reasoning-trace">
                          <div className="trace-summary">
                            <Cpu size={12} />
                            <span>
                              {msg.grade_log.filter(l => l.is_relevant).length}/{msg.grade_log.length} relevant chunks
                            </span>
                          </div>
                          <div className="trace-details">
                            {msg.grade_log.map((log, li) => (
                              <div key={li} className={`trace-item ${log.is_relevant ? 'relevant' : 'irrelevant'}`}>
                                <span className="trace-dot"></span>
                                <span className="trace-reason">{log.reason}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="source-badges">
                      {msg.sources.slice(0, 3).map((s, si) => (
                        <div
                          key={si}
                          className="source-badge clickable"
                          onClick={() => setSelectedSource({ content: s, index: si + 1 })}
                        >
                          <FileText size={10} style={{ marginRight: '4px' }} />
                          Source {si + 1}
                        </div>
                      ))}
                      {msg.sources.length > 3 && (
                        <div
                          className="source-badge clickable"
                          onClick={() => setSelectedSource({ content: msg.sources.join('\n\n---\n\n'), index: 'All' })}
                        >
                          +{msg.sources.length - 3} more
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <div className="message ai">
              <div className="msg-bubble">
                <div className="thinking">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="chat-input-area">
          <div className="input-container">
            <input
              type="text"
              className="main-input"
              placeholder={mode === 'Uploaded Documents' ? "Ask about your data..." : "Search local disk..."}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="send-button" onClick={handleSend} disabled={loading}>
              <Send size={18} />
            </button>
          </div>
          <p style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '1rem' }}>
            DocuSenseAI uses local processing. Your files never leave this machine.
          </p>
        </div>
      </main>

      {/* Source Detail Modal */}
      <AnimatePresence>
        {selectedSource && (
          <div className="modal-overlay" onClick={() => setSelectedSource(null)}>
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="modal-content glass-panel"
              onClick={e => e.stopPropagation()}
            >
              <div className="modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} className="logo-icon" />
                  <h3>Source Detail {selectedSource.index !== 'All' ? `#${selectedSource.index}` : '(Combined)'}</h3>
                </div>
                <button className="close-btn" onClick={() => setSelectedSource(null)}>
                  <Plus size={20} style={{ transform: 'rotate(45deg)' }} />
                </button>
              </div>
              <div className="modal-body">
                <pre>{selectedSource.content}</pre>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
