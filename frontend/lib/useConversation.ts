'use client';

import { useCallback, useMemo, useState } from 'react';

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
};

export type ToolEvent = {
  id: string;
  tool_name: string;
  status: 'start' | 'result' | 'error';
  details?: unknown;
  createdAt: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api';

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function useConversation(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const latestAssistant = useMemo(() => {
    const reversed = [...messages].reverse();
    return reversed.find((m) => m.role === 'assistant');
  }, [messages]);

  const sendMessage = useCallback(async (content: string) => {
    setIsStreaming(true);
    setError(null);

    const userMessage: Message = {
      id: uid('u'),
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    };
    const assistantMessage: Message = {
      id: uid('a'),
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      const response = await fetch(`${API_BASE}/chat/${sessionId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, tool_mode: 'auto' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('stream body is empty');
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
              if (last?.role === 'assistant') {
                last.content += data.delta;
              }
              return next;
            });
          }

          if (event === 'tool_call_start') {
            setToolEvents((prev) => [
              {
                id: uid('t'),
                tool_name: data.tool_name,
                status: 'start',
                details: data,
                createdAt: new Date().toISOString(),
              },
              ...prev,
            ]);
          }
          if (event === 'tool_call_result') {
            setToolEvents((prev) => [
              {
                id: uid('t'),
                tool_name: data.tool_name,
                status: 'result',
                details: data.result,
                createdAt: new Date().toISOString(),
              },
              ...prev,
            ]);
          }
          if (event === 'tool_call_error') {
            setToolEvents((prev) => [
              {
                id: uid('t'),
                tool_name: data.tool_name ?? 'unknown',
                status: 'error',
                details: data,
                createdAt: new Date().toISOString(),
              },
              ...prev,
            ]);
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'unknown error');
    } finally {
      setIsStreaming(false);
    }
  }, [sessionId]);

  return {
    messages,
    toolEvents,
    isStreaming,
    error,
    latestAssistant,
    sendMessage,
  };
}
