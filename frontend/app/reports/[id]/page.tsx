'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Icon, { Icons } from '@/components/Icon'
// import ReactMarkdown from 'react-markdown'
import { SmartBrevityDaily } from '@/app/components/SmartBrevityDaily'
import { WeeklyReview } from '@/app/components/WeeklyReview'
import { formatBeijingDate, formatBeijingDateTimeFromApi, parseYmdAsShanghaiDate } from '@/lib/datetime'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  summary_markdown: string
  analysis_markdown: string | null
  content_json?: any
  article_count: number
  created_at: string
}

export default function ReportDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (params.id) {
      fetchReport(Number(params.id))
    }
  }, [params.id])

  const fetchReport = async (id: number) => {
    try {
      const response = await fetch(`/api/reports/${id}`)
      if (!response.ok) {
        if (response.status === 404) {
          setError('报告不存在')
        } else {
          setError('加载失败')
        }
        return
      }
      const data = await response.json()
      setReport(data)
    } catch (error) {
      console.error('Failed to fetch report:', error)
      setError('加载失败')
    } finally {
      setLoading(false)
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

  if (error) {
    return (
      <div className="container mx-auto px-4 py-16">
        <Card className="max-w-2xl mx-auto">
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Icon name={Icons.fileText} size={48} className="mx-auto text-gray-400 mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{error}</h3>
              <div className="flex gap-4 justify-center mt-6">
                <Link href="/">
                  <Button variant="outline">返回首页</Button>
                </Link>
                <Link href="/admin/reports">
                  <Button>管理后台</Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!report) {
    return null
  }

  const isDaily = report.report_type === 'daily' || report.report_type === 'DAILY'
  const schema = report.content_json?.schema
  const isSmartBrevity = schema === 'smart_brevity_v1'

  return (
    <div className="container mx-auto px-4 py-10 max-w-6xl">
      {/* 返回按钮 */}
      <div className="mb-6">
        <Link href="/">
          <Button variant="ghost" className="gap-2">
            <Icon name={Icons.arrowLeft} size={16} />
            返回首页
          </Button>
        </Link>
      </div>

      {/* 周报：使用 WeeklyReview 组件（仅当 summary_markdown 是纯 Markdown 时） */}
      {!isDaily && report.summary_markdown && !report.summary_markdown.trim().startsWith('<') ? (
        <WeeklyReview
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count || 0}
          summaryMarkdown={report.summary_markdown}
        />
      ) : isSmartBrevity && isDaily ? (
        <SmartBrevityDaily
          reportTypeLabel="晨报"
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count}
          contentJson={report.content_json}
        />
      ) : (
        <Card className="mb-6 shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.9)' }}>
          <CardHeader className={`rounded-t-lg ${isDaily ? 'bg-gradient-to-r from-blue-50 to-indigo-50' : 'bg-gradient-to-r from-purple-50 to-pink-50'}`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Badge className={isDaily ? 'bg-blue-500 hover:bg-blue-600 text-white' : 'bg-purple-500 hover:bg-purple-600 text-white'}>
                    {isDaily ? '晨报' : '周报'}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    {(() => {
                      const d = parseYmdAsShanghaiDate(report.report_date)
                      return d
                        ? formatBeijingDate(d, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
                        : report.report_date
                    })()}
                  </span>
                </div>
                <CardTitle className="text-2xl font-bold text-gray-900">{report.title}</CardTitle>
              </div>
              <Icon name={Icons.fileText} size={32} className={isDaily ? 'text-blue-500' : 'text-purple-500'} />
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4 text-sm text-gray-600 mb-6">
              <div className="flex items-center gap-2">
                <Icon name={Icons.fileText} size={16} />
                <span>包含 {report.article_count} 篇文章</span>
              </div>
              <div className="flex items-center gap-2">
                <Icon name={Icons.calendar} size={16} />
                <span>生成于 {formatBeijingDateTimeFromApi(report.created_at)}</span>
              </div>
            </div>

            {/* 报告内容 */}
            <div
              className="max-w-none"
              dangerouslySetInnerHTML={{ __html: report.summary_markdown }}
            />

            {report.analysis_markdown && (
              <div className="mt-8 pt-8 border-t">
                <h3 className="text-xl font-semibold mb-4">深度分析</h3>
                <div className="max-w-none whitespace-pre-wrap">
                  {report.analysis_markdown}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

