'use client'

import { useEffect, useMemo, useState } from 'react'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'
import { useConfirm } from '@/components/ui/confirm'

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
  const [collecting, setCollecting] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [collectJob, setCollectJob] = useState<any>(null)
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterDate, setFilterDate] = useState<string>('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [totalCount, setTotalCount] = useState<number>(0)
  const { toast } = useToast()
  const { confirm } = useConfirm()

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

  const collectStatusUi = useMemo(() => {
    const status = (collectJob?.status || '').toString()
    if (!status) return null
    if (status === 'running' || status === 'pending') {
      return { label: '采集中', cls: 'bg-white/15 border-white/25 text-white' }
    }
    if (status === 'success') {
      return { label: '完成', cls: 'bg-emerald-500/20 border-emerald-200/30 text-white' }
    }
    if (status === 'failed') {
      return { label: '有错误', cls: 'bg-red-500/20 border-red-200/30 text-white' }
    }
    return { label: status, cls: 'bg-white/15 border-white/25 text-white' }
  }, [collectJob?.status])

  const fetchCollectStatus = async (jobId?: number) => {
    const res = await api.get('/admin/articles/collect/status', { params: jobId ? { job_id: jobId } : {} })
    setCollectJob(res.data || null)
    const st = res.data?.status
    setCollecting(st === 'pending' || st === 'running')
    return res.data
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

  // Restore current collection status on page load and poll while running
  useEffect(() => {
    fetchCollectStatus().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!collecting) return
    const t = window.setInterval(() => {
      fetchCollectStatus(collectJob?.id).catch(() => {})
    }, 2000)
    return () => window.clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collecting, collectJob?.id])

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

  const handleCollect = async () => {
    const ok = await confirm({
      title: '立即采集',
      description: '确定要立即采集所有公众号的最新文章吗？（后台执行，可能需要一些时间）',
      confirmText: '开始采集',
      cancelText: '取消',
    })
    if (!ok) {
      return
    }

    setCollecting(true)
    try {
      const response = await api.post('/admin/articles/collect')
      const jobId = response.data?.job_id
      toast({
        title: '已触发采集',
        description: response.data.message || '采集任务已启动，稍后会自动刷新',
        variant: 'success',
      })
      // start polling status
      await fetchCollectStatus(jobId)
    } catch (error: any) {
      console.error('Failed to collect articles:', error)
      const errorMessage = error.response?.data?.detail || error.message || '采集失败'
      toast({ title: '采集失败', description: errorMessage, variant: 'error' })
    } finally {
      // collecting state is now driven by job status polling
    }
  }

  const handleClearAll = async () => {
    const ok = await confirm({
      title: '清除所有文章',
      description: '这会删除当前数据库里的所有文章（不可撤销）。确定要继续吗？',
      confirmText: '确认清除',
      cancelText: '取消',
    })
    if (!ok) return

    setClearing(true)
    try {
      const resp = await api.post('/admin/articles/clear', undefined, { timeout: 60000 })
      toast({
        title: '已清除',
        description: resp.data?.message || '已清空所有文章',
        variant: 'success',
      })
      setPage(1)
      setSearchInput('')
      setSearchTerm('')
      setFilterStatus('all')
      setFilterDate('')
      await fetchArticles()
    } catch (e: any) {
      console.error(e)
      const msg = e.response?.data?.detail || e.message || '清除失败'
      toast({ title: '清除失败', description: msg, variant: 'error' })
    } finally {
      setClearing(false)
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
      {/* 页面标题区域 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-green-600 via-emerald-600 to-teal-600 p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="text-white">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <Icon name={Icons.fileText} size={40} />
              文章管理
            </h1>
            <p className="text-green-100 text-sm sm:text-base">查看和管理所有采集的文章</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
            <Button
              onClick={handleCollect}
              disabled={collecting || clearing}
              className="bg-white text-green-600 hover:bg-green-50"
            >
              <Icon name={collecting ? Icons.refresh : Icons.download} size={16} className="mr-2" />
              {collecting ? '采集中...' : '立即采集'}
            </Button>
            <Button
              onClick={handleClearAll}
              disabled={collecting || clearing}
              className="bg-red-600 text-white hover:bg-red-700 border-0"
            >
              <Icon name={Icons.delete} size={16} className="mr-2" />
              {clearing ? '清除中...' : '清除所有文章'}
            </Button>
          </div>
        </div>

        {collectJob && (collecting || collectJob.status === 'success' || collectJob.status === 'failed') ? (
          <div className="relative z-10 mt-5 rounded-xl bg-white/10 border border-white/15 p-4 text-white">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {collectStatusUi ? (
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${collectStatusUi.cls}`}>
                    {collectStatusUi.label}
                  </span>
                ) : null}
                <span className="font-semibold">进度</span>
                <span className="tabular-nums">
                  {collectJob.processed_accounts ?? 0}/{collectJob.total_accounts ?? 0}
                </span>
                <span className="opacity-90">账号</span>
                <span className="mx-1 opacity-40">·</span>
                <span className="opacity-90">新增</span>
                <span className="tabular-nums">{collectJob.new_articles ?? 0}</span>
                <span className="mx-1 opacity-40">·</span>
                <span className="opacity-90">错误</span>
                <span className="tabular-nums">{collectJob.error_count ?? 0}</span>
                <span className="mx-1 opacity-40">·</span>
                <span className="opacity-90">模式</span>
                <span className="tabular-nums">{collectJob.mode || '-'}</span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  className="bg-white/90 border-0 text-slate-900 h-9"
                  onClick={() => {
                    fetchCollectStatus(collectJob.id).catch(() => {})
                    fetchArticles().catch(() => {})
                  }}
                >
                  <Icon name={Icons.refresh} size={16} className="mr-2" />
                  刷新状态
                </Button>
              </div>
            </div>

            <div className="mt-3 h-2 w-full rounded-full bg-white/15 overflow-hidden">
              <div
                className="h-2 rounded-full bg-white"
                style={{
                  width:
                    collectJob.total_accounts > 0
                      ? `${Math.min(100, Math.round(((collectJob.processed_accounts || 0) / collectJob.total_accounts) * 100))}%`
                      : '0%',
                }}
              />
            </div>
            {collectJob.last_error ? (
              <div className="mt-2 text-xs text-red-100">最近错误：{collectJob.last_error}</div>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* 筛选和搜索 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.search} size={20} className="text-green-600" />
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
        <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.fileText} size={20} className="text-green-600" />
            文章列表
          </CardTitle>
          <CardDescription>
            共 {totalCount} 篇文章（每页 {pageSize}）
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {articles.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-green-100 to-emerald-100 mb-4">
                <Icon name={Icons.fileText} size={40} className="text-green-400" />
              </div>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">暂无文章</h3>
              <p className="mt-2 text-sm text-gray-500">还没有采集到任何文章</p>
            </div>
          ) : (
            <div className="rounded-lg border border-green-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-green-50 to-emerald-50">
                    <tr className="border-green-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">标题</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden md:table-cell">来源</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">发布时间</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">查看文章</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden xl:table-cell">采集时间</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-green-100">
                    {articles.map((article) => (
                      <tr key={article.id} className="hover:bg-green-50/50 transition-colors">
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
                          <Button asChild variant="outline" className="border-green-200">
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
          <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="text-sm text-muted-foreground">
              第 {page} / {totalPages} 页
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" onClick={() => setPage(1)} disabled={page <= 1}>
                首页
              </Button>
              <Button variant="outline" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                上一页
              </Button>

              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={page}
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    if (!Number.isFinite(v)) return
                    setPage(Math.min(Math.max(1, v), totalPages))
                  }}
                  className="w-20"
                />
                <span className="text-sm text-muted-foreground">/ {totalPages}</span>
              </div>

              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                下一页
              </Button>
              <Button variant="outline" onClick={() => setPage(totalPages)} disabled={page >= totalPages}>
                末页
              </Button>

              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v))
                  setPage(1)
                }}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20 / 页</SelectItem>
                  <SelectItem value="50">50 / 页</SelectItem>
                  <SelectItem value="100">100 / 页</SelectItem>
                  <SelectItem value="200">200 / 页</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

