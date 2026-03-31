import Link from 'next/link';

export default function HomePage() {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <div style={{ maxWidth: 640, textAlign: 'center', border: '1px solid #2a3552', borderRadius: 16, padding: 32, background: '#121a2b' }}>
        <h1 style={{ marginTop: 0 }}>HaoX Health AI</h1>
        <p style={{ color: '#9cb1d9', lineHeight: 1.7 }}>
          生产级聊天界面 Demo（Qwen + MCP 自动工具调用），支持路线规划、知识库检索、深度研究任务。
        </p>
        <Link href="/chat/demo-session" style={{ display: 'inline-block', marginTop: 12, background: '#4f8cff', padding: '10px 16px', borderRadius: 10 }}>
          进入聊天
        </Link>
      </div>
    </main>
  );
}
