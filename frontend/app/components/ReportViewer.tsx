'use client'

import { useState, useEffect } from 'react'
import { SmartBrevityDaily } from './SmartBrevityDaily'
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

interface ReportViewerProps {
  reportId: number | null
  onClose?: () => void
}

export function ReportViewer({ reportId, onClose }: ReportViewerProps) {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (reportId) {
      fetchReport(reportId)
    } else {
      setReport(null)
    }
  }, [reportId])

  const fetchReport = async (id: number) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/reports/${id}`)
      if (response.ok) {
        const data = await response.json()
        setReport(data)
      }
    } catch (error) {
      console.error('Failed to fetch report:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!reportId) {
    return null
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-600 mx-auto"></div>
        <p className="mt-4 text-slate-500">加载中...</p>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>报告不存在</p>
        {onClose && (
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            关闭
          </button>
        )}
      </div>
    )
  }

  const isWeekly = report.report_type === 'weekly' || report.report_type === 'WEEKLY'
  const isDaily = report.report_type === 'daily' || report.report_type === 'DAILY'
  const isSmartBrevity = report.content_json?.schema === 'smart_brevity_v1'

  return (
    <div className="space-y-4">
      {onClose && (
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
          >
            关闭
          </button>
        </div>
      )}
      
      {isWeekly && report.summary_markdown && !report.summary_markdown.trim().startsWith('<') ? (
        <WeeklyReview
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count || 0}
          summaryMarkdown={report.summary_markdown}
        />
      ) : isDaily && isSmartBrevity ? (
        <SmartBrevityDaily
          reportTypeLabel="晨报"
          reportDate={report.report_date}
          createdAt={report.created_at}
          articleCount={report.article_count}
          contentJson={report.content_json}
        />
      ) : report.summary_markdown ? (
        <div className="prose max-w-none bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div dangerouslySetInnerHTML={{ __html: report.summary_markdown }} />
        </div>
      ) : null}
    </div>
  )
}

