'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { isAuthenticated, removeToken } from '@/lib/auth'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import Icon, { Icons } from '@/components/Icon'
import { cn } from '@/lib/utils'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    if (!isAuthenticated() && pathname !== '/admin/login') {
      router.push('/admin/login')
    }
  }, [router, pathname])

  const handleLogout = () => {
    removeToken()
    router.push('/admin/login')
  }

  if (!mounted) {
    return null
  }

  if (pathname === '/admin/login') {
    return <>{children}</>
  }

  const navItems = [
    { href: '/admin', label: '仪表板', icon: Icons.dashboard },
    { href: '/admin/accounts', label: '公众号管理', icon: Icons.accounts },
    { href: '/admin/articles', label: '文章管理', icon: Icons.fileText },
    { href: '/admin/subscribers', label: '订阅管理', icon: Icons.subscribers },
    { href: '/admin/reports', label: '报告管理', icon: Icons.reports },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50" style={{ backgroundSize: '200% 200%', animation: 'gradient 15s ease infinite' }}>
      {/* 装饰性背景元素 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob" style={{ animationDelay: '4s' }}></div>
      </div>

      <div className="relative z-10 border-b shadow-sm backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <div className="container mx-auto flex h-16 items-center px-4">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-lg">
              <Icon name={Icons.settings} size={16} />
            </div>
            <h1 className="text-xl font-bold hidden sm:block bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">Z-Pulse 管理后台</h1>
            <h1 className="text-lg font-bold sm:hidden bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">管理后台</h1>
          </div>
          <nav className="ml-4 sm:ml-8 flex items-center space-x-1 sm:space-x-2 overflow-x-auto md:overflow-x-visible flex-1 no-scrollbar">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap",
                    isActive
                      ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md scale-105"
                      : "text-slate-700 hover:bg-white/60 hover:shadow-sm hover:scale-105"
                  )}
                >
                  <Icon name={item.icon} size={16} className="h-3 w-3 sm:h-4 sm:w-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </Link>
              )
            })}
          </nav>
          <div className="ml-2 sm:ml-auto flex-shrink-0">
            <Button variant="ghost" onClick={handleLogout} className="gap-1 sm:gap-2 h-9 sm:h-10 hover:bg-white/60">
              <Icon name={Icons.logout} size={16} className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">退出登录</span>
              <span className="sm:hidden">退出</span>
            </Button>
          </div>
        </div>
      </div>

      <main className="relative z-10 container mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}
