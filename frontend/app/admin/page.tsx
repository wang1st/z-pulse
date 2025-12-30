'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Link from 'next/link'
import Icon, { Icons } from '@/components/Icon'

interface DashboardStats {
  total_accounts: number
  active_accounts: number
  total_articles: number
  pending_articles: number
  total_subscribers: number
  active_subscribers: number
  total_reports: number
  daily_reports: number
  weekly_reports: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await api.get('/admin/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        无法加载统计数据
      </div>
    )
  }

  const statCards = [
    {
      title: '公众号总数',
      value: stats.total_accounts,
      active: stats.active_accounts,
      href: '/admin/accounts',
      color: 'bg-blue-500',
      icon: Icons.accounts,
    },
    {
      title: '文章总数',
      value: stats.total_articles,
      pending: stats.pending_articles,
      href: '/admin/articles',
      color: 'bg-green-500',
      icon: Icons.fileText,
    },
    {
      title: '订阅者总数',
      value: stats.total_subscribers,
      active: stats.active_subscribers,
      href: '/admin/subscribers',
      color: 'bg-purple-500',
      icon: Icons.subscribers,
    },
    {
      title: '报告总数',
      value: stats.total_reports,
      daily: stats.daily_reports,
      weekly: stats.weekly_reports,
      href: '/admin/reports',
      color: 'bg-orange-500',
      icon: Icons.reports,
    },
  ]

  return (
    <div>
      <div className="px-4 py-5 sm:p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">仪表板</h2>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((card, index) => (
            <Link
              key={index}
              href={card.href}
              className="bg-white overflow-hidden shadow rounded-lg hover:shadow-lg transition-shadow"
            >
              <div className="p-5">
                <div className="flex items-center">
                  <div className={`${card.color} rounded-md p-3 flex items-center justify-center`}>
                    <Icon name={card.icon} size={24} className="text-white" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {card.title}
                      </dt>
                      <dd className="flex items-baseline">
                        <div className="text-2xl font-semibold text-gray-900">
                          {card.value}
                        </div>
                        {card.active !== undefined && (
                          <div className="ml-2 text-sm text-gray-500">
                            (活跃: {card.active})
                          </div>
                        )}
                        {card.pending !== undefined && (
                          <div className="ml-2 text-sm text-yellow-600">
                            (待处理: {card.pending})
                          </div>
                        )}
                        {card.daily !== undefined && (
                          <div className="ml-2 text-sm text-gray-500">
                            (晨报: {card.daily}, 周报: {card.weekly})
                          </div>
                        )}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
