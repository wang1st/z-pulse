'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DailyReportDisplay } from './components/DailyReportDisplay'
import { ReportCalendar } from './components/ReportCalendar'
import { WeeklyReportDisplay } from './components/WeeklyReportDisplay'
import { SmartBrevityDaily } from './components/SmartBrevityDaily'
import { WeeklyReview } from './components/WeeklyReview'
import { SubscribeForm } from './components/SubscribeForm'
import Icon, { Icons } from '@/components/Icon'

export default function Home() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedReport, setSelectedReport] = useState<any | null>(null)

  const handleDateClick = (date: string, report: any) => {
    setSelectedDate(date)
    setSelectedReport(report || null)
  }

  return (
    <main className="min-h-screen bg-white">
      {/* 简洁的头部 */}
      <div className="border-b border-slate-200 bg-white">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-tight text-slate-900">浙财脉动</h1>
              <span className="text-xs text-slate-500">大模型聚合的财政情报</span>
            </div>
            <div />
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* 顶部：晨报显示（优先今天，没有则昨天） */}
        <div className="mb-12">
          <DailyReportDisplay targetDate={selectedDate ?? undefined} />
        </div>

        {/* 中间：报告日历 */}
        <div className="mb-12">
          <ReportCalendar onDateClick={handleDateClick} selectedDate={selectedDate} />
        </div>

        {/* 日历下方：选中日期的报告或本周周报 */}
        <div className="mb-12">
          
          {selectedReport ? (
            (() => {
              const isWeekly =
                selectedReport.report_type === 'weekly' ||
                selectedReport.report_type === 'WEEKLY'
              const summary = selectedReport.summary_markdown || ''
              const trimmed = summary.trim()
              const looksLikeHtml = trimmed.startsWith('<')

              if (isWeekly && summary) {
                if (!looksLikeHtml) {
                  return (
                    <WeeklyReview
                      reportDate={selectedReport.report_date}
                      createdAt={selectedReport.created_at}
                      articleCount={selectedReport.article_count || 0}
                      summaryMarkdown={summary}
                    />
                  )
                }
                return (
                  <div className="prose max-w-none bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: summary,
                      }}
                    />
                  </div>
                )
              }

              return null
            })()
          ) : selectedDate ? null : (
            <WeeklyReportDisplay />
          )}
        </div>
      </div>

      {/* 订阅区域 */}
      <div className="border-t border-slate-200 bg-slate-50">
        <div className="container mx-auto px-4 py-12 max-w-4xl">
          <div className="rounded-3xl border border-slate-200 bg-white p-7 md:p-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
              <div className="max-w-xl">
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">订阅每日晨报</div>
                <div className="mt-2 text-sm md:text-base text-slate-600 leading-relaxed">
                  用邮箱接收"浙财脉动"每日财政信息摘要。我们只发送你订阅的内容，不做营销邮件。
                </div>
              </div>
              <div className="w-full md:max-w-md">
                <SubscribeForm />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-10">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-slate-600">© {new Date().getFullYear()} 浙财脉动 · Z-Pulse</p>
          <div className="mt-4 text-sm">
            <Link href="/about" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              关于我们
            </Link>
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              隐私政策
            </Link>
            <Link href="/contact" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              联系我们
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}
