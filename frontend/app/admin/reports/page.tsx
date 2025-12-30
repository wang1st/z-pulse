'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'
import { useConfirm } from '@/components/ui/confirm'
import { formatBeijingDate, parseYmdAsShanghaiDate } from '@/lib/datetime'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  summary_markdown: string
  analysis_markdown: string | null
  article_count: number
  view_count: number
  sent_count: number
  created_at: string
}

interface ReportJob {
  id: number
  job_type: string
  status: string
  target_date: string
  report_id: number | null
  requested_by: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
  error_message: string
  is_stale: boolean
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [targetDate, setTargetDate] = useState<string>(() => new Date().toISOString().slice(0, 10))
  const [jobs, setJobs] = useState<ReportJob[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('all')
  const [jobTypeFilter, setJobTypeFilter] = useState<string>('all')
  const { toast } = useToast()
  const { confirm } = useConfirm()

  useEffect(() => {
    fetchReports()
  }, [filter])

  const formatBeijing = (value: string | null) => {
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

  const fetchReports = async () => {
    try {
      const params = filter && filter !== 'all' ? { report_type: filter } : {}
      const response = await api.get('/admin/reports', { params })
      setReports(response.data)
    } catch (error) {
      console.error('Failed to fetch reports:', error)
      const anyErr: any = error
      const msg = anyErr?.response?.data?.detail || anyErr?.message || '加载报告失败'
      toast({ title: '加载失败', description: msg, variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const fetchJobs = async () => {
    setJobsLoading(true)
    try {
      const params: any = { limit: 80 }
      if (jobStatusFilter && jobStatusFilter !== 'all') params.status_ = jobStatusFilter
      if (jobTypeFilter && jobTypeFilter !== 'all') params.job_type = jobTypeFilter
      const res = await api.get('/admin/jobs', { params })
      setJobs(res.data?.items || [])
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
      const anyErr: any = error
      const msg = anyErr?.response?.data?.detail || anyErr?.message || '加载任务失败'
      toast({ title: '任务加载失败', description: msg, variant: 'error' })
    } finally {
      setJobsLoading(false)
    }
  }

  // initial load + refresh when filters change
  useEffect(() => {
    fetchJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobStatusFilter, jobTypeFilter])

  // Poll while there are pending/running jobs
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'running')
    if (!hasActive) return
    const t = window.setInterval(() => {
      fetchJobs().catch(() => {})
    }, 5000)
    return () => window.clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs])

  const handleDelete = async (id: number, title: string) => {
    const ok = await confirm({
      title: '删除报告',
      description: `确定要删除报告“${title}”吗？此操作不可撤销。`,
      confirmText: '删除',
      cancelText: '取消',
      variant: 'destructive',
    })
    if (!ok) {
      return
    }

    try {
      await api.delete(`/admin/reports/${id}`)
      fetchReports()
    } catch (error) {
      console.error('Failed to delete report:', error)
      toast({ title: '删除失败', description: '请稍后重试', variant: 'error' })
    }
  }

  const handleForceRegenerateByDate = async (dateStr: string) => {
    const ok = await confirm({
      title: '强制重新生成晨报',
      description: `确定要强制重新生成 ${dateStr} 的晨报吗？（将创建新的后台任务，覆盖卡死/重复任务）`,
      confirmText: '强制生成',
      cancelText: '取消',
      variant: 'destructive',
    })
    if (!ok) return
    try {
      const res = await api.post(`/admin/reports/daily/${dateStr}/regenerate`, null, { params: { force: true } })
      toast({ title: '已提交后台任务', description: res.data?.message || '已强制入队', variant: 'success' })
      fetchJobs()
      fetchReports()
    } catch (error: any) {
      console.error('Failed to force regenerate:', error)
      const errorMessage = error.response?.data?.detail || error.message || '强制生成失败'
      toast({ title: '强制生成失败', description: errorMessage, variant: 'error' })
    }
  }

  const handleCancelJob = async (jobId: number) => {
    const ok = await confirm({
      title: '取消任务',
      description: `确定要取消任务 #${jobId} 吗？（仅对待执行任务生效）`,
      confirmText: '取消任务',
      cancelText: '返回',
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await api.post(`/admin/jobs/${jobId}/cancel`)
      toast({ title: '已取消', description: `任务 #${jobId} 已取消`, variant: 'success' })
      fetchJobs()
    } catch (error: any) {
      console.error('Failed to cancel job:', error)
      const errorMessage = error.response?.data?.detail || error.message || '取消失败'
      toast({ title: '取消失败', description: errorMessage, variant: 'error' })
    }
  }

  const handleReclaimJob = async (jobId: number) => {
    const ok = await confirm({
      title: '回收卡死任务',
      description: `任务 #${jobId} 可能因 worker 重启而卡死在 RUNNING。确定要标记为失败以便重新生成吗？`,
      confirmText: '回收',
      cancelText: '取消',
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await api.post(`/admin/jobs/${jobId}/reclaim`)
      toast({ title: '已回收', description: `任务 #${jobId} 已回收，可重新生成`, variant: 'success' })
      fetchJobs()
    } catch (error: any) {
      console.error('Failed to reclaim job:', error)
      const errorMessage = error.response?.data?.detail || error.message || '回收失败'
      toast({ title: '回收失败', description: errorMessage, variant: 'error' })
    }
  }

  const handleRegenerate = async (reportDate: string, title: string) => {
    const ok = await confirm({
      title: '重新生成报告',
      description: `确定要重新生成“${title}”吗？将基于相同日期文章重新生成。`,
      confirmText: '开始生成',
      cancelText: '取消',
    })
    if (!ok) {
      return
    }

    try {
      // 按日期重新生成：避免 report_id 变化导致的 404
      const dateStr = reportDate.slice(0, 10)
      const response = await api.post(`/admin/reports/daily/${dateStr}/regenerate`)
      toast({
        title: '已提交后台任务',
        description: response.data.message || '正在后台生成，稍后刷新列表或查看报告详情',
        variant: 'success',
      })
      fetchJobs()
      fetchReports()
    } catch (error: any) {
      console.error('Failed to regenerate report:', error)
      const errorMessage = error.response?.data?.detail || error.message || '重新生成失败'
      toast({ title: '重新生成失败', description: errorMessage, variant: 'error' })
    }
  }

  const handleGenerateByDate = async () => {
    if (!targetDate) {
      toast({ title: '请选择日期', description: '请选择要生成的晨报日期', variant: 'error' })
      return
    }

    const ok = await confirm({
      title: '生成指定日期晨报',
      description: `确定要生成 ${targetDate} 的晨报吗？`,
      confirmText: '开始生成',
      cancelText: '取消',
    })
    if (!ok) return

    try {
      const res = await api.post(`/admin/reports/daily/${targetDate}/regenerate`)
      toast({
        title: '已提交后台任务',
        description: res.data?.message || `已提交 ${targetDate} 晨报生成任务`,
        variant: 'success',
      })
      fetchJobs()
      fetchReports()
    } catch (error: any) {
      console.error('Failed to generate report by date:', error)
      const errorMessage = error.response?.data?.detail || error.message || '生成失败'
      toast({ title: '生成失败', description: errorMessage, variant: 'error' })
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
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-orange-600 via-red-600 to-pink-600 p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="text-white">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <Icon name={Icons.reports} size={40} />
              报告管理
            </h1>
            <p className="text-orange-100 text-sm sm:text-base">管理和查看所有生成的报告</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-2 bg-white/90 rounded-lg p-2">
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="h-9 w-[150px] bg-white border-0"
              />
              <Button
                onClick={handleGenerateByDate}
                className="h-9 bg-white text-orange-700 hover:bg-orange-50"
              >
                <Icon name={Icons.refresh} size={16} className="mr-2" />
                生成晨报
              </Button>
            </div>
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="bg-white/90 border-0 w-32">
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="daily">晨报</SelectItem>
                <SelectItem value="weekly">周报</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* 报告列表卡片 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-orange-50 to-red-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.reports} size={20} className="text-orange-600" />
            报告列表
          </CardTitle>
          <CardDescription>查看和管理所有已生成的报告</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {reports.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-orange-100 to-red-100 mb-4">
                <Icon name={Icons.reports} size={40} className="text-orange-400" />
              </div>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">暂无报告</h3>
              <p className="mt-2 text-sm text-gray-500">还没有生成任何报告</p>
            </div>
          ) : (
            <div className="rounded-lg border border-orange-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-orange-50 to-red-50">
                    <tr className="border-orange-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">类型</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">标题</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden md:table-cell">日期</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">统计</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-orange-100">
                    {reports.map((report) => (
                      <tr key={report.id} className="hover:bg-orange-50/50 transition-colors">
                        <td className="px-4 py-4">
                          <Badge variant={(report.report_type === 'daily' || report.report_type === 'DAILY') ? 'default' : 'secondary'} className={(report.report_type === 'daily' || report.report_type === 'DAILY') ? 'bg-blue-500 hover:bg-blue-600' : 'bg-purple-500 hover:bg-purple-600'}>
                            {(report.report_type === 'daily' || report.report_type === 'DAILY') ? '晨报' : '周报'}
                          </Badge>
                        </td>
                        <td className="px-4 py-4">
                          <div className="font-semibold text-gray-900">{report.title}</div>
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell text-gray-600">
                          {(() => {
                            const d = parseYmdAsShanghaiDate(report.report_date)
                            return d ? formatBeijingDate(d) : report.report_date
                          })()}
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell text-gray-600 text-sm">
                          <div className="space-y-1">
                            <div>包含 {report.article_count} 篇文章</div>
                            <div className="text-xs text-gray-500">
                              查看 {report.view_count} 次 · 发送 {report.sent_count} 次
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link href={`/reports/${report.id}`}>
                              <Button variant="ghost" size="sm" className="text-indigo-600 hover:text-indigo-800 hover:bg-indigo-100">
                                <Icon name={Icons.fileText} size={16} className="mr-1" />
                                查看
                              </Button>
                            </Link>
                            {(report.report_type === 'daily' || report.report_type === 'DAILY') && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRegenerate(report.report_date, report.title)}
                                className="text-blue-600 hover:text-blue-800 hover:bg-blue-100"
                                title="重新生成报告"
                              >
                                <Icon name={Icons.refresh} size={16} className="mr-1" />
                                重新生成
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(report.id, report.title)}
                              className="text-red-600 hover:text-red-800 hover:bg-red-100"
                            >
                              <Icon name={Icons.delete} size={16} className="mr-1" />
                              删除
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 任务管理 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-orange-50 to-red-50 rounded-t-lg">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Icon name={Icons.terminal} size={20} className="text-orange-600" />
                任务管理
              </CardTitle>
              <CardDescription>查看后台任务队列、回收卡死任务、强制重跑</CardDescription>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Select value={jobTypeFilter} onValueChange={setJobTypeFilter}>
                <SelectTrigger className="bg-white/90 border w-[180px]">
                  <SelectValue placeholder="任务类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部任务</SelectItem>
                  <SelectItem value="regenerate_daily">晨报再生成</SelectItem>
                </SelectContent>
              </Select>
              <Select value={jobStatusFilter} onValueChange={setJobStatusFilter}>
                <SelectTrigger className="bg-white/90 border w-[160px]">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="pending">待执行</SelectItem>
                  <SelectItem value="running">运行中</SelectItem>
                  <SelectItem value="success">成功</SelectItem>
                  <SelectItem value="failed">失败</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={() => fetchJobs()}
                className="bg-white text-orange-700 hover:bg-orange-50 border border-orange-100"
                disabled={jobsLoading}
              >
                <Icon name={Icons.refresh} size={16} className="mr-2" />
                刷新
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {jobs.length === 0 ? (
            <div className="text-center py-10 text-sm text-gray-500">暂无任务记录</div>
          ) : (
            <div className="rounded-lg border border-orange-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-orange-50 to-red-50">
                    <tr className="border-orange-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">类型</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">日期</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">状态</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden lg:table-cell">时间</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 hidden xl:table-cell">信息</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-orange-100">
                    {jobs.map((j) => {
                      const status = (j.status || '').toLowerCase()
                      const statusBadge =
                        status === 'pending'
                          ? { text: '待执行', cls: 'bg-gray-100 text-gray-700' }
                          : status === 'running'
                            ? { text: j.is_stale ? '运行中(疑似卡死)' : '运行中', cls: j.is_stale ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700' }
                            : status === 'success'
                              ? { text: '成功', cls: 'bg-emerald-100 text-emerald-700' }
                              : { text: '失败', cls: 'bg-red-100 text-red-700' }

                      return (
                        <tr key={j.id} className="hover:bg-orange-50/50 transition-colors">
                          <td className="px-4 py-4 text-sm text-gray-700 tabular-nums whitespace-nowrap">#{j.id}</td>
                          <td className="px-4 py-4 text-sm text-gray-700 whitespace-nowrap">
                            {j.job_type === 'regenerate_daily' ? '晨报再生成' : j.job_type}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-700 tabular-nums whitespace-nowrap">{j.target_date}</td>
                          <td className="px-4 py-4">
                            <Badge className={statusBadge.cls}>{statusBadge.text}</Badge>
                          </td>
                          <td className="px-4 py-4 text-xs text-gray-600 hidden lg:table-cell whitespace-nowrap tabular-nums">
                            <div className="space-y-1">
                              <div>创建：{formatBeijing(j.created_at)}</div>
                              {j.started_at ? <div>开始：{formatBeijing(j.started_at)}</div> : null}
                              {j.finished_at ? <div>结束：{formatBeijing(j.finished_at)}</div> : null}
                            </div>
                          </td>
                          <td className="px-4 py-4 text-xs text-gray-600 hidden xl:table-cell">
                            <div className="space-y-1">
                              <div>触发：{j.requested_by || '-'}</div>
                              {j.report_id ? (
                                <div>
                                  报告：
                                  <Link className="text-indigo-700 hover:underline" href={`/reports/${j.report_id}`}>
                                    #{j.report_id}
                                  </Link>
                                </div>
                              ) : null}
                              {j.error_message ? <div className="text-red-700 line-clamp-2">错误：{j.error_message}</div> : null}
                            </div>
                          </td>
                          <td className="px-4 py-4 text-right">
                            <div className="flex items-center justify-end gap-2 flex-wrap">
                              {j.job_type === 'regenerate_daily' ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleForceRegenerateByDate(j.target_date)}
                                  className="text-orange-700 hover:text-orange-900 hover:bg-orange-100"
                                  title="强制重跑（force=true）"
                                >
                                  <Icon name={Icons.refresh} size={16} className="mr-1" />
                                  强制重跑
                                </Button>
                              ) : null}
                              {status === 'pending' ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCancelJob(j.id)}
                                  className="text-red-600 hover:text-red-800 hover:bg-red-100"
                                >
                                  <Icon name={Icons.delete} size={16} className="mr-1" />
                                  取消
                                </Button>
                              ) : null}
                              {status === 'running' && j.is_stale ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleReclaimJob(j.id)}
                                  className="text-red-600 hover:text-red-800 hover:bg-red-100"
                                >
                                  <Icon name={Icons.delete} size={16} className="mr-1" />
                                  回收
                                </Button>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
