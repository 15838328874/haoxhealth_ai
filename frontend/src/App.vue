<script setup lang="ts">
import { computed, ref } from 'vue'

type Message = { id: string; role: 'user' | 'assistant'; content: string; createdAt: string }
type ToolEvent = { id: string; toolName: string; status: 'start' | 'result' | 'error'; details: unknown; createdAt: string }

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'
const sessionId = ref('demo-session')
const input = ref('')
const messages = ref<Message[]>([])
const toolEvents = ref<ToolEvent[]>([])
const isStreaming = ref(false)
const error = ref('')

const canSend = computed(() => input.value.trim().length > 0 && !isStreaming.value)

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

async function sendMessage() {
  if (!canSend.value) return
  const content = input.value.trim()
  input.value = ''
  error.value = ''
  isStreaming.value = true

  messages.value.push({ id: uid('u'), role: 'user', content, createdAt: new Date().toISOString() })
  const assistant: Message = { id: uid('a'), role: 'assistant', content: '', createdAt: new Date().toISOString() }
  messages.value.push(assistant)

  try {
    const response = await fetch(`${API_BASE}/chat/${sessionId.value}/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content, model: 'qwen-plus', tool_mode: 'auto', temperature: 0.3, max_tokens: 1200 }),
    })

    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''

      for (const block of blocks) {
        const eventMatch = block.match(/event: (.+)/)
        const dataMatch = block.match(/data: (.+)/)
        if (!eventMatch || !dataMatch) continue
        const event = eventMatch[1]
        const data = JSON.parse(dataMatch[1])

        if (event === 'message_delta') assistant.content += data.delta ?? ''
        if (event === 'tool_call_start' || event === 'tool_call_result' || event === 'tool_call_error') {
          toolEvents.value.unshift({
            id: uid('t'),
            toolName: data.tool_name ?? data.toolName ?? 'unknown',
            status: event === 'tool_call_start' ? 'start' : event === 'tool_call_result' ? 'result' : 'error',
            details: data,
            createdAt: new Date().toISOString(),
          })
        }
        if (event === 'error') {
          error.value = `${data.code ?? 'MODEL_ERROR'}: ${data.message ?? 'unknown error'}`
        }
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'unknown error'
  } finally {
    isStreaming.value = false
  }
}
</script>

<template>
  <div class="layout">
    <header>
      <h1>haoxhealth AI · Vue Chat</h1>
      <span>Session: {{ sessionId }}</span>
    </header>
    <main>
      <section class="chat">
        <article v-for="msg in messages" :key="msg.id" :class="['bubble', msg.role]">
          <p>{{ msg.content }}</p>
        </article>
      </section>
      <aside>
        <h3>Tool Events</h3>
        <div v-for="evt in toolEvents" :key="evt.id" class="evt">
          <strong>{{ evt.toolName }}</strong>
          <span>{{ evt.status }}</span>
        </div>
      </aside>
    </main>
    <footer>
      <input v-model="input" placeholder="输入问题，如：从杭州东站到西湖怎么走" @keydown.enter="sendMessage" />
      <button :disabled="!canSend" @click="sendMessage">{{ isStreaming ? '生成中...' : '发送' }}</button>
    </footer>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>
