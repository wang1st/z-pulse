'use client'

import { useState } from 'react'

export function SubscribeForm() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')

    try {
      // 避免 FastAPI 对 /api/subscribe 做 307 -> /api/subscribe/ 的重定向（POST 重定向在部分环境会引入不确定性）
      const response = await fetch('/api/subscribe/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (response.ok) {
        setStatus('success')
        setMessage(data.message || '订阅成功！请检查您的邮箱完成验证。')
        setEmail('')
      } else {
        setStatus('error')
        setMessage(data.detail || '订阅失败，请稍后重试')
      }
    } catch (error) {
      setStatus('error')
      setMessage('网络错误，请稍后重试')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="请输入您的邮箱地址"
          autoComplete="email"
          inputMode="email"
          aria-label="邮箱地址"
          required
          style={{
            // Safari 有时会用 -webkit-text-fill-color 覆盖 color（尤其是自动填充/深色表单控件场景）
            color: '#0f172a',
            WebkitTextFillColor: '#0f172a',
          }}
          className="w-full px-4 py-3 rounded-lg border border-white/15 !bg-white !text-slate-900 placeholder:!text-slate-400 caret-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-0 disabled:opacity-60"
          disabled={status === 'loading'}
        />
      </div>

      <button
        type="submit"
        disabled={status === 'loading'}
        className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-medium rounded-lg hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {status === 'loading' ? '提交中...' : '订阅'}
      </button>

      {message && (
        <div
          className={`p-4 rounded-lg ${
            status === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {message}
        </div>
      )}

      <p className="text-sm text-gray-500 text-center">
        订阅即表示您同意我们的{' '}
        <a href="/privacy" className="text-purple-600 hover:underline">
          隐私政策
        </a>
      </p>
    </form>
  )
}

