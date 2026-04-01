'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useConversation } from '@/lib/useConversation';

const demoSessions = [
  { id: 'demo-session', title: '默认会话' },
  { id: 'research-room', title: '深度研究' },
  { id: 'route-planning', title: '路线规划' },
];

function formatTime(iso: string) {
  const date = new Date(iso);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function ChatPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params?.sessionId ?? 'demo-session';

  const { messages, toolEvents, isStreaming, error, latestAssistant, sendMessage } = useConversation(sessionId);
  const [text, setText] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isStreaming) return;
    const toSend = text;
    setText('');
    await sendMessage(toSend);
  };

  const sessionStats = useMemo(() => {
    const userCount = messages.filter((m) => m.role === 'user').length;
    const assistantCount = messages.filter((m) => m.role === 'assistant').length;
    return { userCount, assistantCount, total: messages.length };
  }, [messages]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-dot" />
          <div>
            <h1>HaoX Health AI</h1>
            <p>Qwen 驱动聊天助手</p>
          </div>
        </div>

        <button className="new-chat-btn">+ 新建会话</button>

        <nav className="session-list">
          {demoSessions.map((item) => (
            <a key={item.id} href={`/chat/${item.id}`} className={`session-item ${item.id === sessionId ? 'active' : ''}`}>
              <span>{item.title}</span>
              <small>{item.id}</small>
            </a>
          ))}
        </nav>

        <div className="sidebar-foot">
          <p>在线工具：{toolEvents.length}</p>
          <p>消息总数：{sessionStats.total}</p>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <div>
            <h2>{sessionId}</h2>
            <p>模型：<strong>qwen-plus</strong> · tool_mode=auto</p>
          </div>
          <div className="header-badges">
            <span>用户消息 {sessionStats.userCount}</span>
            <span>助手消息 {sessionStats.assistantCount}</span>
          </div>
        </header>

        <section className="chat-body">
          {messages.length === 0 && (
            <div className="empty-state">
              <h3>开始你的第一条消息</h3>
              <p>支持自动调用：高德路线、知识库检索、深度研究任务。</p>
            </div>
          )}

          {messages.map((m) => (
            <article key={m.id} className={`bubble-wrap ${m.role}`}>
              <div className="avatar">{m.role === 'user' ? '你' : 'AI'}</div>
              <div className="bubble">
                <p>{m.content || (m.role === 'assistant' ? '正在思考中…' : '')}</p>
                <time>{formatTime(m.createdAt)}</time>
              </div>
            </article>
          ))}
        </section>

        <footer className="chat-input-wrap">
          {error && <div className="error-banner">请求失败：{error}</div>}
          <form onSubmit={onSubmit} className="chat-input-form">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="输入你的问题，例如：帮我规划从杭州东站到西湖的路线"
              rows={3}
            />
            <div className="action-row">
              <div className="hint">
                {isStreaming ? '正在流式生成...' : latestAssistant ? `最近回复：${latestAssistant.content.slice(0, 32) || '...'}...` : '按 Enter 发送'}
              </div>
              <button type="submit" disabled={isStreaming || !text.trim()}>
                {isStreaming ? '生成中...' : '发送'}
              </button>
            </div>
          </form>
        </footer>
      </main>

      <aside className="right-panel">
        <h3>工具调用动态</h3>
        <div className="tool-feed">
          {toolEvents.length === 0 && <p className="muted">暂无工具调用</p>}
          {toolEvents.map((evt) => (
            <div key={evt.id} className={`tool-card ${evt.status}`}>
              <div className="tool-title">
                <strong>{evt.tool_name}</strong>
                <span>{evt.status}</span>
              </div>
              <time>{formatTime(evt.createdAt)}</time>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
