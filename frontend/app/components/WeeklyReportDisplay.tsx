'use client'

import { useEffect, useState } from 'react'
import { WeeklyReview } from './WeeklyReview'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  summary_markdown: string
  content_json?: any
  article_count: number
  created_at: string
}

export function WeeklyReportDisplay() {
  const [weeklyReport, setWeeklyReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLatestWeeklyReport()
  }, [])

  const fetchLatestWeeklyReport = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/reports/latest/weekly')
      if (response.ok) {
        const data = await response.json()
        if (data) {
          // 检查是否是本周的周报（周报的report_date是周一，所以检查是否在最近7天内）
          const today = new Date()
          const reportDate = new Date(data.report_date)
          const daysDiff = Math.floor((today.getTime() - reportDate.getTime()) / (1000 * 60 * 60 * 24))
          // 如果周报日期在最近7天内，认为是"本周的周报"
          if (daysDiff >= 0 && daysDiff <= 6) {
            setWeeklyReport(data)
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch weekly report:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return null // 加载时不显示任何内容
  }

  if (!weeklyReport) {
    return null // 没有周报时不显示
  }

  const summary = weeklyReport.summary_markdown || ''
  const trimmed = summary.trim()
  const looksLikeHtml = trimmed.startsWith('<')

  // 新版周报：Markdown，用 WeeklyReview 组件渲染
  if (summary && !looksLikeHtml) {
    return (
      <div className="mb-12">
        <WeeklyReview
          reportDate={weeklyReport.report_date}
          createdAt={weeklyReport.created_at}
          articleCount={weeklyReport.article_count || 0}
          summaryMarkdown={summary}
        />
      </div>
    )
  }

  // 旧版周报：HTML，直接渲染
  if (summary) {
    return (
      <div className="mb-12">
        <div className="prose max-w-none bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div dangerouslySetInnerHTML={{ __html: summary }} />
        </div>
      </div>
    )
  }

  return null
}

