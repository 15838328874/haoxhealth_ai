'use client';

import { FormEvent, useState } from 'react';
import { useParams } from 'next/navigation';
import { useConversation } from '@/lib/useConversation';

export default function ChatPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params?.sessionId ?? 'demo-session';
  const { messages, toolEvents, isStreaming, sendMessage } = useConversation(sessionId);
  const [text, setText] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    const toSend = text;
    setText('');
    await sendMessage(toSend);
  };

  return (
    <main className="container">
      <section>
        <h2>会话：{sessionId}</h2>
        <div className="panel">
          {messages.map((m, idx) => (
            <p key={idx}><b>{m.role}:</b> {m.content}</p>
          ))}
        </div>
        <form onSubmit={onSubmit} className="row">
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="输入内容..." />
          <button type="submit" disabled={isStreaming}>发送</button>
        </form>
      </section>
      <aside>
        <h3>工具事件</h3>
        <div className="panel">
          {toolEvents.map((evt, idx) => (
            <p key={idx}>[{evt.status}] {evt.tool_name}</p>
          ))}
        </div>
      </aside>
    </main>
  );
}
