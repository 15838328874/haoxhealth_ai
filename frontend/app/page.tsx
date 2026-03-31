import Link from 'next/link';

export default function HomePage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>haoxhealth-ai</h1>
      <p>进入聊天页体验MCP自动工具调用。</p>
      <Link href="/chat/demo-session">打开聊天</Link>
    </main>
  );
}
