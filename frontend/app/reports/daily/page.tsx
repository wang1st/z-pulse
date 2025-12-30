'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Icon, { Icons } from '@/components/Icon'
// import ReactMarkdown from 'react-markdown'
import { SmartBrevityDaily } from '@/app/components/SmartBrevityDaily'
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

export default function DailyReportPage() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchLatestDailyReport()
  }, [])

  const fetchLatestDailyReport = async () => {
    try {
      const response = await fetch('/api/reports/latest/daily')
      if (!response.ok) {
        if (response.status === 404) {
          setError('暂无晨报')
        } else {
          setError('加载失败')
        }
        return
      }
      const data = await response.json()
      setReport(data)
    } catch (error) {
      console.error('Failed to fetch daily report:', error)
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
              <p className="text-gray-500 mb-6">还没有生成晨报，请稍后再试</p>
              <Link href="/">
                <Button variant="outline">返回首页</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!report) {
    return null
  }

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

      {isSmartBrevity ? (
        <SmartBrevityDaily
          reportTypeLabel="晨报"
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count}
          contentJson={report.content_json}
        />
      ) : (
        <Card className="mb-6 shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.9)' }}>
          <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Badge className="bg-blue-500 hover:bg-blue-600 text-white">
                    晨报
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
              <Icon name={Icons.fileText} size={32} className="text-blue-500" />
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

            {/* 报告内容（后端已渲染为 HTML） */}
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

