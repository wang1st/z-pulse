'use client'

import { useEffect, useMemo, useState } from 'react'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import Link from 'next/link'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'


interface Article {
  id: number
  account_id: number
  account_name?: string
  title: string
  content: string | null
  article_url: string
  published_at: string
  status: string
  collected_at: string
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterDate, setFilterDate] = useState<string>('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [totalCount, setTotalCount] = useState<number>(0)
  const { toast } = useToast()

  const formatBeijing = (value: string) => {
    if (!value) return ''
    const dt = new Date(value)
    if (isNaN(dt.getTime())) return value
    const s = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(dt)
    return s.replaceAll('/', '-')
  }


  useEffect(() => {
    const t = setTimeout(() => {
      setSearchTerm(searchInput.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    fetchArticles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, filterDate, searchTerm, page, pageSize])


  const fetchArticles = async () => {
    try {
      const params: any = {}
      params.skip = (page - 1) * pageSize
      params.limit = pageSize
      if (filterStatus !== 'all') {
        params.status = filterStatus
      }
      if (filterDate) {
        params.date = filterDate
      }
      if (searchTerm) {
        params.search = searchTerm
      }
      const response = await api.get('/admin/articles', { params, timeout: 20000 })
      setArticles(response.data)
      const total = Number(response.headers?.['x-total-count'] ?? 0)
      setTotalCount(Number.isFinite(total) ? total : 0)
    } catch (error) {
      console.error('Failed to fetch articles:', error)
      toast({ title: '加载失败', description: '获取文章列表超时或失败，请稍后重试', variant: 'error' })
    } finally {
      setLoading(false)
    }
  }


  const totalPages = useMemo(() => {
    if (!totalCount) return 1
    return Math.max(1, Math.ceil(totalCount / pageSize))
  }, [totalCount, pageSize])

  const clampedPage = useMemo(() => {
    return Math.min(Math.max(1, page), totalPages)
  }, [page, totalPages])

  useEffect(() => {
    if (clampedPage !== page) setPage(clampedPage)
  }, [clampedPage, page])

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
      {/* 页面标题区域 - 统一使用 Indigo/Purple 渐变 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="text-white">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <Icon name={Icons.fileText} size={40} />
              文章管理
            </h1>
            <p className="text-indigo-100 text-sm sm:text-base">查看和管理文章内容</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 sm:items-center"></div>
        </div>
      </div>

      {/* 筛选和搜索 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.search} size={20} className="text-indigo-600" />
            筛选和搜索
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-center">
            <div className="lg:col-span-2">
              <Input
                placeholder="搜索文章标题或内容..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                className="w-full"
              />
            </div>
            <div>
              <Select
                value={filterStatus}
                onValueChange={(v) => {
                  setFilterStatus(v)
                  setPage(1)
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="全部状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="PENDING">待处理</SelectItem>
                  <SelectItem value="PROCESSED">已处理</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Input
                type="date"
                value={filterDate}
                onChange={(e) => {
                  setFilterDate(e.target.value)
                  setPage(1)
                }}
                placeholder="选择日期"
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 文章列表 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.fileText} size={20} className="text-indigo-600" />
            文章列表
          </CardTitle>
          <CardDescription>
            共 {totalCount} 篇文章（每页 {pageSize}）
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {articles.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 mb-4">
                <Icon name={Icons.fileText} size={40} className="text-indigo-400" />
              </div>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">暂无文章</h3>
              <p className="mt-2 text-sm text-gray-500">暂无文章数据</p>
            </div>
          ) : (
            <div className="rounded-lg border border-indigo-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-indigo-50 to-purple-50">
                    <tr className="border-indigo-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">标题</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden md:table-cell">来源</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">发布时间</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">查看文章</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden xl:table-cell">采集时间</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-indigo-100">
                    {articles.map((article) => (
                      <tr key={article.id} className="hover:bg-indigo-50/50 transition-colors">
                        <td className="px-4 py-4">
                          <div className="font-semibold text-gray-900 line-clamp-2">{article.title}</div>
                          {article.content && (
                            <div className="text-sm text-gray-500 mt-1 line-clamp-1">
                              {article.content.substring(0, 100)}...
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell text-gray-600">
                          {article.account_name || `账号 ${article.account_id}`}
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell text-gray-600">
                          <span className="whitespace-nowrap tabular-nums text-sm">{formatBeijing(article.published_at)}</span>
                        </td>
                        <td className="px-4 py-4">
                          <Button asChild variant="outline" className="border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600">
                            <Link href={`/admin/articles/${article.id}`}>查看</Link>
                          </Button>
                        </td>
                        <td className="px-4 py-4 hidden xl:table-cell text-gray-600 text-sm">
                          <span className="whitespace-nowrap tabular-nums text-sm">{formatBeijing(article.collected_at)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 分页导航 */}
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-600">第 {page} / {totalPages} 页</div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">每页</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v))
                  setPage(1)
                }}
              >
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="200">200</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                className="text-gray-700 hover:bg-indigo-100"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </Button>
              <Button
                variant="ghost"
                className="text-gray-700 hover:bg-indigo-100"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
