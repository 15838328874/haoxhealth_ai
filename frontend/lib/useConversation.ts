'use client';

import { useCallback, useState } from 'react';

export type Message = { role: 'user' | 'assistant'; content: string };
export type ToolEvent = { tool_name: string; status: 'start' | 'result' | 'error'; details?: unknown };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api';

export function useConversation(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: 'user', content }, { role: 'assistant', content: '' }]);

    const response = await fetch(`${API_BASE}/chat/${sessionId}/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content, tool_mode: 'auto' }),
    });

    if (!response.body) {
      setIsStreaming(false);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const raw of events) {
        const eventMatch = raw.match(/event: (.+)/);
        const dataMatch = raw.match(/data: (.+)/);
        if (!eventMatch || !dataMatch) continue;
        const event = eventMatch[1];
        const data = JSON.parse(dataMatch[1]);

        if (event === 'message_delta') {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'assistant') last.content += data.delta;
            return next;
          });
        }
        if (event === 'tool_call_start') {
          setToolEvents((prev) => [...prev, { tool_name: data.tool_name, status: 'start', details: data }]);
        }
        if (event === 'tool_call_result') {
          setToolEvents((prev) => [...prev, { tool_name: data.tool_name, status: 'result', details: data.result }]);
        }
        if (event === 'tool_call_error') {
          setToolEvents((prev) => [...prev, { tool_name: data.tool_name ?? 'unknown', status: 'error', details: data }]);
        }
      }
    }

    setIsStreaming(false);
  }, [sessionId]);

  return { messages, toolEvents, isStreaming, sendMessage };
}
