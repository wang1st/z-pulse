'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import Icon, { Icons } from '@/components/Icon'
import { SmartBrevityDaily } from '@/app/components/SmartBrevityDaily'
import { WeeklyReview } from '@/app/components/WeeklyReview'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  summary_markdown: string
  analysis_markdown: string | null
  article_count: number
  created_at: string
  content_json: any
}

export default function WeeklyReportPage() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchLatestWeeklyReport()
  }, [])

  const fetchLatestWeeklyReport = async () => {
    try {
      const response = await fetch('/api/reports/latest/weekly')
      if (!response.ok) {
        if (response.status === 404) {
          setError('暂无周报')
        } else {
          setError('加载失败')
        }
        return
      }
      const data = await response.json()
      setReport(data)
    } catch (error) {
      console.error('Failed to fetch weekly report:', error)
      setError('加载失败')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-300 mx-auto"></div>
          <p className="mt-4 text-slate-500">加载中...</p>
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
              <Icon name={Icons.fileText} size={48} className="mx-auto text-slate-400 mb-4" />
              <h3 className="text-xl font-semibold text-slate-900 mb-2">{error}</h3>
              <p className="text-slate-500 mb-6">还没有生成周报，请稍后再试</p>
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

  // 如果有summary_markdown，使用WeeklyReview组件（新格式：一周述评）
  if (report.summary_markdown) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-6">
          <Link href="/">
            <Button variant="ghost" className="gap-2">
              <Icon name={Icons.arrowLeft} size={16} />
              返回首页
            </Button>
          </Link>
        </div>
        <WeeklyReview
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count || 0}
          summaryMarkdown={report.summary_markdown}
        />
      </div>
    )
  }

  // 如果有content_json，使用SmartBrevity组件（向后兼容）
  if (report.content_json) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-6">
          <Link href="/">
            <Button variant="ghost" className="gap-2">
              <Icon name={Icons.arrowLeft} size={16} />
              返回首页
            </Button>
          </Link>
        </div>
        <SmartBrevityDaily
          reportTypeLabel="周报"
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count || 0}
          contentJson={report.content_json}
        />
      </div>
    )
  }

  // 旧版HTML渲染（向后兼容）
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <Link href="/">
          <Button variant="ghost" className="gap-2">
            <Icon name={Icons.arrowLeft} size={16} />
            返回首页
          </Button>
        </Link>
      </div>

      <Card className="shadow-lg border border-slate-200 bg-white/95 backdrop-blur-sm">
        <CardContent className="p-8">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-slate-900 mb-4">{report.title}</h1>
            <div className="flex flex-wrap gap-4 text-sm text-slate-600">
              <span>包含 {report.article_count} 篇文章</span>
              <span>·</span>
              <span>生成于 {report.created_at}</span>
            </div>
          </div>

          <div
            className="prose prose-slate max-w-none"
            dangerouslySetInnerHTML={{ __html: report.summary_markdown || '' }}
          />

          {report.analysis_markdown && (
            <div className="mt-8 pt-8 border-t border-slate-200">
              <h3 className="text-xl font-semibold mb-4">深度分析</h3>
              <div className="prose prose-slate max-w-none whitespace-pre-wrap">
                {report.analysis_markdown}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

