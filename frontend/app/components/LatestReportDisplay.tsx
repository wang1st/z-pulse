'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { SmartBrevityDaily } from './SmartBrevityDaily'
import { WeeklyReview } from './WeeklyReview'
import { formatBeijingYmd } from '@/lib/datetime'

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

export function LatestReportDisplay() {
  const [weeklyReport, setWeeklyReport] = useState<Report | null>(null)
  const [dailyReport, setDailyReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLatestReports()
  }, [])

  const fetchLatestReports = async () => {
    try {
      // 获取最新的周报和晨报
      const [weeklyRes, dailyRes] = await Promise.all([
        fetch('/api/reports/latest/weekly').catch(() => null),
        fetch('/api/reports/latest/daily').catch(() => null)
      ])
      
      if (weeklyRes && weeklyRes.ok) {
        try {
          const weeklyData = await weeklyRes.json()
          if (weeklyData) {
            // 检查是否是今天的周报（周报的report_date是周一，所以检查是否在最近7天内）
            const today = new Date()
            const reportDate = new Date(weeklyData.report_date)
            const daysDiff = Math.floor((today.getTime() - reportDate.getTime()) / (1000 * 60 * 60 * 24))
            // 如果周报日期在最近7天内，认为是"今天的周报"
            if (daysDiff >= 0 && daysDiff <= 6) {
              setWeeklyReport(weeklyData)
            }
          }
        } catch (e) {
          // 忽略JSON解析错误
        }
      }
      
      if (dailyRes && dailyRes.ok) {
        try {
          const dailyData = await dailyRes.json()
          if (dailyData) {
            // 检查是否是今天的晨报
            const today = new Date().toISOString().split('T')[0] // 使用 YYYY-MM-DD 格式
            const reportDate = dailyData.report_date.split('T')[0]
            if (reportDate === today) {
              setDailyReport(dailyData)
            }
          }
        } catch (e) {
          // 忽略JSON解析错误
          console.error('Error parsing daily report:', e)
        }
      }
    } catch (error) {
      console.error('Failed to fetch latest reports:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-600 mx-auto"></div>
        <p className="mt-4 text-slate-500">加载中...</p>
      </div>
    )
  }

  // 优先显示周报，如果没有则显示晨报
  const primaryReport = weeklyReport || dailyReport

  if (!primaryReport) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>今天还没有报告</p>
        <Link href="/reports/daily" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
          查看历史报告 →
        </Link>
      </div>
    )
  }

  const isWeekly = primaryReport.report_type === 'weekly' || primaryReport.report_type === 'WEEKLY'
  const isDaily = primaryReport.report_type === 'daily' || primaryReport.report_type === 'DAILY'
  const isSmartBrevity = primaryReport.content_json?.schema === 'smart_brevity_v1'

  return (
    <div className="space-y-8">
      {/* 主要报告（周报或晨报） */}
      {isWeekly && primaryReport.summary_markdown && !primaryReport.summary_markdown.trim().startsWith('<') ? (
        <WeeklyReview
          reportDate={primaryReport.report_date}
          createdAt={primaryReport.created_at}
          articleCount={primaryReport.article_count || 0}
          summaryMarkdown={primaryReport.summary_markdown}
        />
      ) : isDaily && isSmartBrevity ? (
        <SmartBrevityDaily
          reportTypeLabel="晨报"
          reportDate={primaryReport.report_date}
          createdAt={primaryReport.created_at}
          articleCount={primaryReport.article_count}
          contentJson={primaryReport.content_json}
        />
      ) : null}

      {/* 如果有周报，也显示今天的晨报 */}
      {weeklyReport && dailyReport && (
        <div className="mt-8 pt-8 border-t border-slate-200">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">今日晨报</h2>
          {dailyReport.content_json?.schema === 'smart_brevity_v1' ? (
            <SmartBrevityDaily
              reportTypeLabel="晨报"
              reportDate={dailyReport.report_date}
              createdAt={dailyReport.created_at}
              articleCount={dailyReport.article_count}
              contentJson={dailyReport.content_json}
            />
          ) : dailyReport.summary_markdown ? (
            <div className="prose max-w-none bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <div dangerouslySetInnerHTML={{ __html: dailyReport.summary_markdown }} />
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

