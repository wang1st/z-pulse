'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login, setToken } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Icon, { Icons } from '@/components/Icon'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await login({ username, password })
      setToken(response.access_token)
      router.push('/admin')
    } catch (err: any) {
      setError(err.message || '用户名或密码错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        backgroundColor: '#f9fafb', // bg-gray-50 的十六进制值
      }}
    >
      <div className="w-full max-w-md">
        {/* Logo和标题 */}
        <div className="text-center mb-8">
          <div 
            className="inline-flex items-center justify-center w-16 h-16 rounded-xl mb-4 shadow-lg"
            style={{
              backgroundColor: '#4f46e5', // bg-indigo-600
            }}
          >
            <Icon name={Icons.shield} size={32} className="text-white" />
          </div>
          <h1 
            className="text-3xl font-bold mb-2"
            style={{ color: '#111827' }} // text-gray-900
          >
            Z-Pulse
          </h1>
          <p 
            className="text-gray-600"
            style={{ color: '#4b5563' }}
          >
            管理后台登录
          </p>
        </div>

        {/* 登录表单 */}
        <Card 
          className="shadow-lg border-0"
          style={{
            backgroundColor: '#ffffff',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
          }}
        >
          <CardHeader className="space-y-1 pb-6">
            <CardTitle 
              className="text-2xl font-semibold text-center"
              style={{ color: '#111827' }}
            >
              欢迎回来
            </CardTitle>
            <CardDescription 
              className="text-center"
              style={{ color: '#6b7280' }}
            >
              请输入您的登录凭据
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleSubmit}>
              {/* 错误提示 */}
              {error && (
                <div 
                  className="px-4 py-3 rounded-lg flex items-start gap-2"
                  style={{
                    backgroundColor: '#fef2f2',
                    borderLeft: '4px solid #ef4444',
                    color: '#b91c1c',
                  }}
                >
                  <Icon name={Icons.error} size={20} className="flex-shrink-0 mt-0.5" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              {/* 用户名输入 */}
              <div className="space-y-2">
                <Label 
                  htmlFor="username" 
                  className="text-sm font-medium"
                  style={{ color: '#374151' }}
                >
                  用户名
                </Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Icon name={Icons.user} size={20} style={{ color: '#9ca3af' }} />
                  </div>
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    required
                    autoComplete="username"
                    className="pl-10 h-11"
                    style={{
                      backgroundColor: '#ffffff',
                      borderColor: '#d1d5db',
                      color: '#111827',
                    }}
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={loading}
                  />
                </div>
              </div>

              {/* 密码输入 */}
              <div className="space-y-2">
                <Label 
                  htmlFor="password" 
                  className="text-sm font-medium"
                  style={{ color: '#374151' }}
                >
                  密码
                </Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Icon name={Icons.lock} size={20} style={{ color: '#9ca3af' }} />
                  </div>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    className="pl-10 h-11"
                    style={{
                      backgroundColor: '#ffffff',
                      borderColor: '#d1d5db',
                      color: '#111827',
                    }}
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                  />
                </div>
              </div>

              {/* 登录按钮 */}
              <Button
                type="submit"
                disabled={loading}
                className="w-full h-11 text-base font-medium text-white"
                style={{
                  backgroundColor: '#4f46e5', // indigo-600
                  border: 'none',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#4338ca' // indigo-700
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#4f46e5'
                }}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    登录中...
                  </>
                ) : (
                  <>
                    <Icon name={Icons.lock} size={16} className="mr-2" />
                    登录
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* 底部信息 */}
        <div className="mt-6 text-center">
          <p className="text-xs" style={{ color: '#6b7280' }}>
            财政信息AI晨报系统管理平台
          </p>
          <p className="text-xs mt-2" style={{ color: '#9ca3af' }}>
            © 2024 Z-Pulse. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  )
}
