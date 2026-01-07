'use client'

import { useEffect, useState } from 'react'
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

interface DailyReportDisplayProps {
  targetDate?: string // YYYY-MM-DD格式，如果未提供则显示今天或昨天的晨报
}

export function DailyReportDisplay({ targetDate }: DailyReportDisplayProps) {
  const [dailyReport, setDailyReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDailyReport()
  }, [targetDate])

  const fetchDailyReport = async () => {
    setLoading(true)
    try {
      let reportDate = targetDate
      
      // 如果没有指定日期，优先获取今天的，没有则获取昨天的
      if (!reportDate) {
        const today = new Date().toISOString().split('T')[0]
        const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        
        // 先尝试获取今天的
        try {
          const todayRes = await fetch(`/api/reports/?report_type=daily&start_date=${today}&end_date=${today}&limit=1`)
          if (todayRes.ok) {
            const todayData = await todayRes.json()
            if (todayData && todayData.length > 0) {
              setDailyReport(todayData[0])
              setLoading(false)
              return
            }
          }
        } catch (e) {
          console.error('Failed to fetch today report:', e)
        }
        
        // 如果没有今天的，获取昨天的
        try {
          const yesterdayRes = await fetch(`/api/reports/?report_type=daily&start_date=${yesterday}&end_date=${yesterday}&limit=1`)
          if (yesterdayRes.ok) {
            const yesterdayData = await yesterdayRes.json()
            if (yesterdayData && yesterdayData.length > 0) {
              setDailyReport(yesterdayData[0])
              setLoading(false)
              return
            }
          }
        } catch (e) {
          console.error('Failed to fetch yesterday report:', e)
        }
        
        setLoading(false)
        return
      }
      
      // 如果指定了日期，获取该日期的晨报
      try {
        const response = await fetch(`/api/reports/?report_type=daily&start_date=${reportDate}&end_date=${reportDate}&limit=1`)
        if (response.ok) {
          const data = await response.json()
          if (data && data.length > 0) {
            setDailyReport(data[0])
          }
        }
      } catch (e) {
        console.error('Failed to fetch report for date:', e)
      }
    } catch (error) {
      console.error('Failed to fetch daily report:', error)
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

  if (!dailyReport) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>该日期还没有晨报</p>
      </div>
    )
  }

  const isSmartBrevity = 
    dailyReport.content_json?.schema === 'smart_brevity_v1' ||
    !!(dailyReport.content_json?.header && (dailyReport.content_json?.recent_hotspots || dailyReport.content_json?.keywords))

  return (
    <div>
      {isSmartBrevity ? (
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
  )
}

