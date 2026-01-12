'use client'

import ReactMarkdown from 'react-markdown'
import { formatBeijingYmd, parseYmdAsShanghaiDate } from '@/lib/datetime'

export function WeeklyReview(props: {
  reportDate: string
  createdAt: string
  articleCount: number
  summaryMarkdown: string
}) {
  const { reportDate, createdAt, articleCount, summaryMarkdown } = props

  // Format date for display: same logic as SmartBrevityDaily
  const formattedDate = (() => {
    // If reportDate is already a range format (contains "至"), use it directly
    if (reportDate.includes('至')) {
      // Extract date range from "2025年12月16日 至 12月22日" format
      const match = reportDate.match(/(\d{4})年(\d{1,2})月(\d{1,2})日\s*至\s*(\d{1,2})月(\d{1,2})日/)
      if (match) {
        const [, , startMonth, startDay, endMonth, endDay] = match
        return `${startMonth}月${startDay}日-${endMonth}月${endDay}日`
      }
      return reportDate
    }
    
    // Otherwise, parse as single date and calculate range
    const d = parseYmdAsShanghaiDate(reportDate)
    if (!d) return reportDate
    
    // For weekly: calculate date range (7 days before reportDate)
    const startDate = new Date(d)
    startDate.setDate(startDate.getDate() - 6) // 7 days including today
    const startMonth = startDate.getMonth() + 1
    const startDay = startDate.getDate()
    const endMonth = d.getMonth() + 1
    const endDay = d.getDate()
    return `${startMonth}月${startDay}日-${endMonth}月${endDay}日`
  })()

  return (
    <div className="mb-16">
      {/* Hero Section - same style as SmartBrevityDaily */}
      <div className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-slate-950 to-slate-950 text-white shadow-2xl mb-6">
        <div className="relative p-5 md:p-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between max-w-6xl mx-auto gap-3 md:gap-4">
            <div className="flex-1">
              <h1 className="text-3xl sm:text-4xl md:text-6xl font-bold tracking-tight text-white mb-1.5 md:mb-4 leading-tight">浙财脉动</h1>
              <p className="text-sm sm:text-base md:text-lg text-white/80 leading-snug">
                大模型聚合的财政情报 · 每周一11点更新
              </p>
            </div>
            <div className="flex flex-row items-center justify-between md:flex-col md:items-end gap-2 md:gap-0 shrink-0">
              <div className="text-xs sm:text-sm md:text-base font-bold text-white whitespace-nowrap">{formattedDate}</div>
              <div className="text-xs md:text-sm font-semibold text-white/90 bg-white/10 px-2 py-0.5 rounded whitespace-nowrap">周报</div>
            </div>
          </div>
        </div>
      </div>

      {/* 一周述评 Section */}
      <div className="bg-white rounded-3xl shadow-xl overflow-hidden mb-6 border-l-4 border-amber-600">
        {/* 标题栏 */}
        <div className="bg-gradient-to-r from-slate-50 to-amber-50/30 px-6 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-600 flex items-center justify-center shadow-md">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900">一周述评</div>
              <div className="text-sm text-gray-600 mt-0.5">全面梳理本周财政动态的整体脉络</div>
            </div>
          </div>
        </div>
        
        {/* 内容区 */}
        <div className="p-8 md:p-10 pl-10 md:pl-12 bg-slate-50/20">
          {(() => {
            const parts = summaryMarkdown.split('\\n\\n---\\n\\n')
            const main = parts[0] || ''
            const disclaimer = parts[1] || ''
            return (
              <>
                <div className="prose prose-slate max-w-none prose-p:text-xl prose-p:!text-xl">
                  <ReactMarkdown
                    components={{
                      h1: ({node, ...props}) => (
                        <h1 className="text-3xl font-bold text-slate-900 mb-6 mt-0 first:mt-0" {...props} />
                      ),
                      h2: ({node, ...props}) => (
                        <h2 className="text-2xl font-semibold text-slate-800 mb-4 mt-6" {...props} />
                      ),
                      h3: ({node, ...props}) => (
                        <h3 className="text-xl font-semibold text-slate-700 mb-3 mt-4" {...props} />
                      ),
                      p: ({node, ...props}) => (
                        <p 
                          className="leading-relaxed text-slate-700 mb-4 indent-8"
                          style={{
                            fontSize: '1.25rem',
                            lineHeight: '1.75'
                          }}
                          {...props} 
                        />
                      ),
                      ul: ({node, ...props}) => (
                        <ul className="list-disc list-inside mb-4 space-y-2 text-slate-700" {...props} />
                      ),
                      ol: ({node, ...props}) => (
                        <ol className="list-decimal list-inside mb-4 space-y-2 text-slate-700" {...props} />
                      ),
                      li: ({node, ...props}) => (
                        <li className="text-xl leading-relaxed" style={{ fontSize: '1.25rem' }} {...props} />
                      ),
                      strong: ({node, ...props}) => (
                        <strong className="font-semibold text-slate-900" {...props} />
                      ),
                      code: ({node, ...props}) => (
                        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono text-slate-800" {...props} />
                      ),
                    }}
                  >
                    {main}
                  </ReactMarkdown>
                </div>
                {disclaimer ? (
                  <div className="prose prose-slate prose-xs max-w-none text-slate-500 mt-6">
                    <ReactMarkdown
                      components={{
                        p: ({node, ...props}) => (
                          <p className="text-xs sm:text-sm leading-relaxed" {...props} />
                        ),
                      }}
                    >
                      {disclaimer}
                    </ReactMarkdown>
                  </div>
                ) : null}
              </>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
