'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'
import { useConfirm } from '@/components/ui/confirm'
import { formatBeijingDateTimeFromApi } from '@/lib/datetime'

interface Subscriber {
  id: number
  email: string
  is_active: boolean
  subscribe_daily: boolean
  subscribe_weekly: boolean
  regions: any
  total_sent: number
  last_sent_at: string | null
  created_at: string
  activated_at: string | null
}

export default function SubscribersPage() {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([])
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()
  const { confirm } = useConfirm()
  const [page, setPage] = useState<number>(0)
  const [limit, setLimit] = useState<number>(20)
  const [hasNext, setHasNext] = useState<boolean>(false)

  useEffect(() => {
    setPage(0)
    fetchSubscribers()
  }, [limit])

  const fetchSubscribers = async () => {
    try {
      const params: any = { skip: page * limit, limit }
      const response = await api.get('/admin/subscribers', { params })
      const list: Subscriber[] = response.data || []
      setSubscribers(list)
      setHasNext(list.length === limit)
    } catch (error) {
      console.error('Failed to fetch subscribers:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number, email: string) => {
    const ok = await confirm({
      title: '删除订阅者',
      description: `确定要删除订阅者 ${email} 吗？此操作不可撤销。`,
      confirmText: '删除',
      cancelText: '取消',
      variant: 'destructive',
    })
    if (!ok) {
      return
    }

    try {
      await api.delete(`/admin/subscribers/${id}`)
      fetchSubscribers()
    } catch (error) {
      console.error('Failed to delete subscriber:', error)
      toast({ title: '删除失败', description: '请稍后重试', variant: 'error' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题区域 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 text-white">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
            <Icon name={Icons.subscribers} size={40} />
            订阅管理
          </h1>
          <p className="text-purple-100 text-sm sm:text-base">管理和监控所有订阅者信息</p>
        </div>
      </div>

      {/* 订阅者列表卡片 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.subscribers} size={20} className="text-purple-600" />
            订阅者列表
          </CardTitle>
          <CardDescription>管理所有已注册的订阅者账号</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {subscribers.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-purple-100 to-pink-100 mb-4">
                <Icon name={Icons.subscribers} size={40} className="text-purple-400" />
              </div>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">暂无订阅者</h3>
              <p className="mt-2 text-sm text-gray-500">还没有任何订阅者注册</p>
            </div>
          ) : (
            <div className="rounded-lg border border-purple-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-purple-50 to-pink-50">
                    <tr className="border-purple-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">状态</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">邮箱</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden md:table-cell">订阅类型</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">统计</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">注册时间</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-purple-100">
                    {subscribers.map((subscriber) => (
                      <tr key={subscriber.id} className="hover:bg-purple-50/50 transition-colors">
                        <td className="px-4 py-4">
                          <Badge variant={subscriber.is_active ? 'default' : 'secondary'} className={subscriber.is_active ? 'bg-green-500 hover:bg-green-600' : 'bg-yellow-500 hover:bg-yellow-600'}>
                            {subscriber.is_active ? '已激活' : '待激活'}
                          </Badge>
                        </td>
                        <td className="px-4 py-4">
                          <div className="font-semibold text-gray-900">{subscriber.email}</div>
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell">
                          <div className="flex gap-2">
                            {subscriber.subscribe_daily && (
                              <span className="px-2 py-1 rounded-md bg-blue-100 text-blue-700 text-xs font-medium">晨报</span>
                            )}
                            {subscriber.subscribe_weekly && (
                              <span className="px-2 py-1 rounded-md bg-purple-100 text-purple-700 text-xs font-medium">周报</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell text-gray-600 text-sm">
                          已发送 {subscriber.total_sent} 次
                          {subscriber.last_sent_at && (
                            <div className="text-xs text-gray-500 mt-1">
                              最后发送: {formatBeijingDateTimeFromApi(subscriber.last_sent_at)}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell text-gray-500 text-sm">
                          {formatBeijingDateTimeFromApi(subscriber.created_at)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(subscriber.id, subscriber.email)}
                            className="text-red-600 hover:text-red-800 hover:bg-red-100"
                          >
                            <Icon name={Icons.delete} size={16} className="mr-1" />
                            删除
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-purple-200">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">每页</span>
                  <select
                    className="border rounded px-2 py-1 text-sm"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-purple-100"
                    disabled={page === 0}
                    onClick={() => {
                      if (page > 0) {
                        setPage(page - 1)
                        fetchSubscribers()
                      }
                    }}
                  >
                    上一页
                  </Button>
                  <span className="text-sm text-gray-600">第 {page + 1} 页</span>
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg紫-100"
                    disabled={!hasNext}
                    onClick={() => {
                      if (hasNext) {
                        setPage(page + 1)
                        fetchSubscribers()
                      }
                    }}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
